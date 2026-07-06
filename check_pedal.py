import pygame

pygame.init()
pygame.joystick.init()

print("Joystick count:", pygame.joystick.get_count())

for i in range(pygame.joystick.get_count()):
    js = pygame.joystick.Joystick(i)
    js.init()

    print("Index:", i)
    print("Name:", js.get_name())
    print("Axes:", js.get_numaxes())
    print("Buttons:", js.get_numbuttons())
    print()



import pyglet.input

for dev in pyglet.input.get_joysticks():
    print(dev.device.name)

