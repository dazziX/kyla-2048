import random
import os
import sys
import pickle
import contextlib
import copy
with contextlib.redirect_stdout(None):
    import pygame
import tween

pygame.init()

LOCAL_DIR = os.path.dirname(__file__)
def resource_path(relative_path):
	""" Get absolute path to resource, works for dev and for PyInstaller """
	"""
	try:
		# PyInstaller creates a temp folder and stores path in _MEIPASS
		base_path = sys._MEIPASS
	except Exception:
		base_path = os.path.abspath(".")
	"""

	return os.path.join(LOCAL_DIR, relative_path)

FOGSANS = resource_path("FogSans.otf")

WIN_WIDTH, WIN_HEIGHT = 540, 660
FPS = 60
CELLSIZE = 109  # this is making me fucking insane
row_multiplier = lambda x: 150 + (15+CELLSIZE)*x
col_multiplier = lambda x: 30 + (15+CELLSIZE)*x
BG_COLOR, GRIDFG_COLOR, GRIDBG_COLOR = pygame.Color("#FBF8F0"), pygame.Color("#F1A3C6"), pygame.Color("#EBBDD0")
DARK_TEXT, LIGHT_TEXT = pygame.Color("#cf82a5"), pygame.Color("#FFDCEB")
TILE_COLORS = [pygame.Color("#F3D5E9"), pygame.Color("#EDC8E1"), pygame.Color("#F498CD"), pygame.Color("#F075BB"), pygame.Color("#F05FAF"), pygame.Color("#F44EAC"), pygame.Color("#FFA7C1"), pygame.Color("#F499B4"), pygame.Color("#F57A9F"), pygame.Color("#F66490"), pygame.Color("#F64D80")]
TILE_FS = 40
SCORE_FONT = pygame.font.Font(FOGSANS, 20)
H_FONT = pygame.font.Font(FOGSANS, 30)
SMALLTEXT_FONT = pygame.font.Font(FOGSANS, 13)
SMALLSCORE_FONT = pygame.font.Font(FOGSANS, 19)
SCORE_LABEL = SMALLTEXT_FONT.render("SCORE", True, GRIDBG_COLOR)
HI_SCORE_LABEL = SMALLTEXT_FONT.render("HIGH SCORE", True, GRIDBG_COLOR)
KYLA_FONT = pygame.font.Font(FOGSANS, 64)
KYLA_FONT.set_italic(True)
KYLA_TEXT = KYLA_FONT.render("kyla", True, DARK_TEXT)
_2048_F = pygame.font.Font(FOGSANS, 64)
#_2048_F.set_italic(True)
_2048_TEXT = _2048_F.render("2048", True, TILE_COLORS[9])
HEART = H_FONT.render(":3", True, DARK_TEXT)


def save_obj(data, filename):
	with open(resource_path(filename), "wb") as f:
		pickle.dump(data, f)

def load_obj(filename):
	with open(resource_path(filename), "rb") as f:
		return pickle.load(f)

OPACITY_DECREMENT = 5
Y_DECREMENT = 1.5

class Popup:

	def __init__(self, value, pool):

		pool.append(self)

		self.value = value
		self.opacity = 255
		self.y = 80

	def blit(self, window):
		render = SMALLSCORE_FONT.render(f"+{self.value}", True, DARK_TEXT)
		render.set_alpha(round(self.opacity))
		rect = render.get_rect(center=(510, self.y))
		window.blit(render, rect)

	def animate(self, pool):
		self.opacity -= OPACITY_DECREMENT
		self.y -= Y_DECREMENT

		if self.opacity <= 0:
			pool.remove(self)


class Tile:

	def __init__(self, value, row, col, board, index=0, scale=0.0):

		self.value = value
		self.row = row
		self.col = col
		self.trow = row
		self.tcol = col
		self.board = board
		self.x = col_multiplier(col)
		self.y = row_multiplier(row)
		self.tx, self.ty = col_multiplier(col), row_multiplier(row)
		self.scale = scale
		self.index = index
		self.spawned = True
		self.added = False
		self.tweening = False

		self.to_combine = None
		self.font_render = pygame.font.Font(FOGSANS, round(TILE_FS*self.scale)).render(str(self.value), True, DARK_TEXT if self.value < 5 else LIGHT_TEXT) # 5

	# add constructor

	def updateFont(self): # this will get called only during animation to save memory
		self.font_render = pygame.font.Font(FOGSANS, round(TILE_FS*self.scale)).render(str(self.value), True, DARK_TEXT if self.value < 5 else LIGHT_TEXT)

	def getRect(self, bg_tile):
		rect = bg_tile.scale_by(self.scale)
		rect.center = bg_tile.center
		return rect

	def addUp(self, tile=None):
		self.index += 1
		self.value += tile.value
		self.updateFont()
		self.added = True

	def animate(self, dt):
		if self.spawned:
			if self.scale < 1:
				self.scale += 0.1
				if self.scale > 1:
					self.scale = 1
					self.spawned = False
			self.updateFont()

		if self.added:
			if self.scale < 1.25:
				self.scale += 0.125
			elif self.scale >= 1.25:
				self.scale = 1.25
				self.added = False
				self.tween_added = tween.to(self, "scale", 1, 0.2, "easeOutCubic")
				self.tween_added.on_update(self.updateFont)
		
	def easeOutTween(self):
		self.tweening = True

	def setTarget(self, row, col):
		h = [0, 1, 2, 3]
		self.trow = h[row]
		self.tcol = h[col]
		self.tx = col_multiplier(self.tcol)
		self.ty = row_multiplier(self.trow)

	def setTargetCombine(self):
		self.trow = self.to_combine.trow
		self.tcol = self.to_combine.tcol
		self.tx = col_multiplier(self.tcol)
		self.ty = row_multiplier(self.trow)

	def updatePos(self):
		self.row = self.trow
		self.col = self.tcol

	def startTween(self, horizontal):
		self.scale = 1

		if horizontal:
			self.tween_moving = tween.to(self, "x", self.tx, 0.11, "linear")
		else:
			self.tween_moving = tween.to(self, "y", self.ty, 0.11, "linear")

		self.tween_moving.on_update(self.updateFont)
		self.tween_moving.on_complete(self.updatePos)
		self.tween_moving.on_complete(self.board.finishTweening)




class Board2048:

	def __init__(self, animationsOn=True):

		self.grid = [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]] # row, col
		self.popups = []
		self.score = 0
		if os.path.isfile(os.path.join(LOCAL_DIR, "highscore.dat")):
			self.high_score = load_obj("highscore.dat")
		else:
			self.high_score = 0

		self.score_render = None
		self.hi_score_render = None

		self.updateScoreboards()

		# instantiate

		for _ in range(2):
			self.addRandomTile()

		self.last_grid = self.grid
		self.last_score = self.score

		self.moving = False
		self.tweening_finished = False

		self.dirx = 1
		self.diry = 0



	@classmethod
	def setWindow(cls, win_w, win_h, title):
		cls.window = pygame.display.set_mode([win_w, win_h])
		pygame.display.set_caption(title)

	def finishTweening(self):
		self.tweening_finished = True

	def save(self):
		int_grid = []
		for row in self.grid:
			int_grid.append([(cell.value, cell.index) if cell!=0 else 0 for cell in row])

		save_obj({"grid": int_grid, "score": self.score}, "checkpoint.dat")

	def load(self):
		last_saved = load_obj("checkpoint.dat")

		self.grid = []
		for r, row in enumerate(last_saved["grid"]):
			self.grid.append([Tile(cell[0], r, c, self, index=cell[1]) if cell!=0 else 0 for c, cell in enumerate(row)])

		self.score = last_saved["score"]
		self.updateScoreboards()

	def getRandomAvailableCell(self):
		a = (random.randint(0, 3), random.randint(0, 3))
		return a if self.grid[a[0]][a[1]] == 0 else self.getRandomAvailableCell()

	def addRandomTile(self):
		value = 2 if random.random() < 0.9 else 4
		cell = self.getRandomAvailableCell()
		self.insertTile(Tile(value, cell[0], cell[1], self, index=1 if value == 4 else 0), cell)

	def insertTile(self, tile, cell):
		self.grid[cell[0]][cell[1]] = tile

	def combineCells(self, x, y, y_row, y_col):  # x doesnt move and y gets deleted
		x.addUp(y)
		self.grid[y_row][y_col] = 0
		self.score += x.value
		self.updateScoreboards()

		return x.value

	def moveCell(self, x_row, x_col, y_row, y_col):  # y will move to x
		self.grid[x_row][x_col] = self.grid[y_row][y_col]
		self.grid[y_row][y_col] = 0

	def updateScoreboards(self):
		# print(self.score)
		if self.high_score < self.score:
			self.high_score = self.score
			save_obj(self.score, "highscore.dat")

		self.score_render = SCORE_FONT.render(str(self.score), True, TILE_COLORS[8])
		self.hi_score_render = SCORE_FONT.render(str(self.high_score), True, TILE_COLORS[8])

	def displayConsole(self):
		for row in self.grid:
			for cell in row:
				print("-", end="\t") if cell == 0 else print(cell.value, end="\t")
			print()

	def step(self, dirx, diry): # move the tiles then add random tile
		# use two values as args - x and y
		if self.moving:
			return

		self.dirx = dirx
		self.diry = diry

		griddy = []
		for r in self.grid:
			griddy.append(r.copy())

		moved = False
		scored = False

		last_grid, last_score = self.saveLastState()

		# dirx 1 : left
		# dirx -1 : right
		# diry 1 : up
		# diry -1 : down
		for r in range(4):
			for i in range(4):
				p = 0+i if dirx == 1 or diry == 1 else -1-i
				x1 = r if diry == 0 else p
				y1 = p if diry == 0 else r
				piss = dirx + diry
				cell = griddy[x1][y1]
				if cell != 0:
					if cell.to_combine != None:
						continue

					n = 4-i
					for b in range(1, n):
						x2 = r if diry == 0 else p+(b*piss)
						y2 = p+(b*piss) if diry == 0 else r
						nearest_cell = griddy[x2][y2]
						if nearest_cell != 0:
							if nearest_cell.value == cell.value:
								nearest_cell.to_combine = cell
								griddy[x2][y2] = 0
								moved = True
								scored = True
							break

			for i in range(4):
				p = 0+i if dirx == 1 or diry == 1 else -1-i
				x1 = r if diry == 0 else p
				y1 = p if diry == 0 else r
				piss = dirx + diry
				cell = griddy[x1][y1]
				if cell == 0:
					n = 4-i
					for b in range(1, n):
						x2 = r if diry == 0 else p+(b*piss)
						y2 = p+(b*piss) if diry == 0 else r
						nearest_cell = griddy[x2][y2]
						if nearest_cell != 0:
							if nearest_cell.to_combine != None:
								continue

							# self.moveCell(x1, y1, x2, y2)
							nearest_cell.setTarget(x1, y1)
							nearest_cell.startTween(True if diry == 0 else False)
							griddy[x1][y1] = griddy[x2][y2]
							griddy[x2][y2] = 0
							moved = True
							break

				cell = self.grid[x1][y1]
				if cell != 0:
					if cell.to_combine != None:
						cell.setTargetCombine()
						cell.startTween(True if diry == 0 else False)



		if moved:
			#self.addRandomTile()
			self.last_grid = last_grid
			self.moving = True
		if scored:
			#self.updateScoreboards()
			self.last_score = last_score
			self.moving = True
			#Popup(total, self.popups)

	def updateBoard(self):

		moved = False
		scored = False
		total = 0

		# last_grid, last_score = self.saveLastState()

		# dirx 1 : left
		# dirx -1 : right
		# diry 1 : up
		# diry -1 : down
		for r in range(4):
			for i in range(4):
				p = 0+i if self.dirx == 1 or self.diry == 1 else -1-i
				x1 = r if self.diry == 0 else p
				y1 = p if self.diry == 0 else r
				piss = self.dirx + self.diry
				cell = self.grid[x1][y1]
				if cell != 0:

					n = 4-i
					for b in range(1, n):
						x2 = r if self.diry == 0 else p+(b*piss)
						y2 = p+(b*piss) if self.diry == 0 else r
						nearest_cell = self.grid[x2][y2]
						if nearest_cell != 0:
							if nearest_cell.value == cell.value:
								total += self.combineCells(cell, nearest_cell, x2, y2)
								moved = True
								scored = True
							break

			for i in range(4):
				p = 0+i if self.dirx == 1 or self.diry == 1 else -1-i
				x1 = r if self.diry == 0 else p
				y1 = p if self.diry == 0 else r
				piss = self.dirx + self.diry
				cell = self.grid[x1][y1]
				if cell == 0:
					n = 4-i
					for b in range(1, n):
						x2 = r if self.diry == 0 else p+(b*piss)
						y2 = p+(b*piss) if self.diry == 0 else r
						nearest_cell = self.grid[x2][y2]
						if nearest_cell != 0:
							self.moveCell(x1, y1, x2, y2)
							moved = True
							break


		if moved:
			self.addRandomTile()
			# self.last_grid = last_grid
		if scored:
			self.updateScoreboards()
			# self.last_score = last_score 
			Popup(total, self.popups)

		self.moving = False
		self.tweening_finished = False



	def saveLastState(self): # I HAVE TO FIX THIS!!
		last_grid = []
		last_score = self.score
		for row in self.grid:
			last_grid.append([copy.copy(cell) if cell != 0 else 0 for cell in row])

		return last_grid, last_score

	def undo(self):
		self.grid = self.last_grid
		self.score = self.last_score
		self.updateScoreboards()

	def animateA(self, dt): # give values to the tiles nd stuff so it like has a cool animation (run every frame if moved = True)
		for row in self.grid:
			for cell in row:
				if cell != 0:
					cell.animate(dt)

		for popup in self.popups:
			popup.animate(self.popups)

		tween.update(dt)

		if self.tweening_finished:
			self.updateBoard()

	def draw_window(self):
		Board2048.window.fill(BG_COLOR)
		grid = pygame.Rect(15, 135, 510, 510)

		pygame.draw.rect(Board2048.window, GRIDFG_COLOR, grid, border_radius=16)

		hi_score_rect = HI_SCORE_LABEL.get_rect(midleft=(30, 118))
		hi_score_i = self.hi_score_render.get_rect(midleft=(30, 100))

		score_rect = SCORE_LABEL.get_rect(midright=(510, 118))
		score_i = self.score_render.get_rect(midright=(510, 100))

		Board2048.window.blit(KYLA_TEXT, KYLA_TEXT.get_rect(midleft=(30, 40)))
		Board2048.window.blit(_2048_TEXT, _2048_TEXT.get_rect(midleft=(152, 40)))
		Board2048.window.blit(HEART, HEART.get_rect(bottomleft=(308, 40)))

		Board2048.window.blit(HI_SCORE_LABEL, hi_score_rect)
		Board2048.window.blit(self.hi_score_render, hi_score_i)
		Board2048.window.blit(SCORE_LABEL, score_rect)
		Board2048.window.blit(self.score_render, score_i)

		for popup in self.popups:
			popup.blit(Board2048.window)

		for row, cells in enumerate(self.grid):
			pos_top = row_multiplier(row)
			for col, c in enumerate(cells):
				pos_left = col_multiplier(col)
				bg_cell = pygame.Rect(pos_left, pos_top, CELLSIZE, CELLSIZE)
				pygame.draw.rect(Board2048.window, GRIDBG_COLOR, bg_cell, border_radius=7)

				"""
				if c != 0:
					tile_rect = c.getRect(bg_cell)
					t_render = pygame.draw.rect(Board2048.window, TILE_COLORS[c.index], tile_rect, border_radius=7)
					text_rect = c.font_render.get_rect(center=t_render.center)
					Board2048.window.blit(c.font_render, text_rect)
				"""

		for row in range(4):
			for i in range(4):
				p = 0+i if self.dirx == -1 or self.diry == -1 else -1-i
				x1 = row if self.diry == 0 else p
				y1 = p if self.diry == 0 else row
				c = self.grid[x1][y1]
				if c != 0:
					tile_rect = c.getRect(pygame.Rect(c.x, c.y, CELLSIZE, CELLSIZE))
					t_render = pygame.draw.rect(Board2048.window, TILE_COLORS[c.index], tile_rect, border_radius=7)
					text_rect = c.font_render.get_rect(center=t_render.center)
					Board2048.window.blit(c.font_render, text_rect)
				



pygame_icon = pygame.image.load(resource_path("main.ico"))
pygame.display.set_icon(pygame_icon)	


def play():
	Board2048.setWindow(WIN_WIDTH, WIN_HEIGHT, "i miss u")
	board = Board2048()

	if os.path.isfile(os.path.join(LOCAL_DIR, "checkpoint.dat")):
		board.load()

	print("i love you")
	clock = pygame.time.Clock()

	dt = clock.tick(FPS) / 1000.0
	running = True
	# board.displayConsole()
	while running:
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				running = False
				board.save()
			elif event.type == pygame.KEYDOWN:
				if event.key == pygame.K_SLASH or event.key == pygame.K_q and board.moving == False:
					print("undo")
					board.undo()
				elif event.key == pygame.K_SPACE:
					board = Board2048()
				elif event.key == pygame.K_UP or event.key == pygame.K_w:
					board.step(0, 1)
				elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
					board.step(0, -1)
				elif event.key == pygame.K_LEFT or event.key == pygame.K_a:
					board.step(1, 0)
				elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
					board.step(-1, 0)

		
		board.animateA(dt)
		board.draw_window()
		pygame.display.update()
		print(clock.get_fps())
		dt = clock.tick(FPS) / 1000.0

	pygame.quit()

play()