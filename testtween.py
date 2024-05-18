import sys
import pygame
from pygame.locals import QUIT
import tween

pygame.init()
screen = pygame.display.set_mode([400,400])
clock = pygame.time.Clock()
dt = 0.0

class Character:
  def __init__(self, surface, x, y):
    self.sprite = surface
    self.x = x
    self.y = y

  def draw(surface):
    surface.blit(self.sprite, (self.x, self.y))

hero_image = pygame.image.load("restart.png")
hero = Character(hero_image, 0, 200)
hero_tween = tween.to(hero, "x", 400, 5.0, "easeInOutQuad") #Starting a tween.

def say_message():
  print("Started moving!")
hero_tween.on_start(say_message) #Adding function that runs at the start of the tween-
  #.on_start() will only have an effect if you call it before the first time the tween is updated

def update(dt):
  tween.update(dt) #Updating all active tweens within the default group

def draw(surface):
  surface.fill((255,255,255))
  hero.draw(surface)
  pygame.display.flip()

while 1:
  for event in pygame.event.get():
    if event.type == QUIT:
     sys.exit()
  update(dt)
  print(screen)
  draw(screen)
  dt = clock.tick(60) / 1000.0 #Divide by 1000.0 to get dt (time_passed) in seconds