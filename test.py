from communications.communications import Comms
from threading import Thread
from postprocessing.world import World
import time
import serial
"""

"""

def getPos():
	Coms.com.ser.write(bytes('Y'))
	time.sleep(1)
	with open(Coms.com.outputFilename) as f:
		log = f.readlines()
		positions = log[len(log)-2]
		positions = [int(pos) for pos in positions.split() if pos[1:].isdigit() or pos.isdigit()]
	#positions[3] = left wheel;
	#positions[5] = right wheel;
	#positions[4] = omni wheel;
	#positions[2] = kicker;
	return positions

def resetPos():
	Coms.com.ser.write(bytes('Z'))
	time.sleep(1)
	with open(Coms.com.outputFilename) as f:
		log = f.readlines()
		positions = log[len(log)-2]
		positions = [int(pos) for pos in positions.split() if pos[1:].isdigit() or pos.isdigit()]
	return positions

if __name__ == "__main__" :

	# setup World model
	World.set_colours('yellow' , 'pink')
	pitch_number = int(0)
	World.set_globals(0 , 'left')

	# start Coms
	comms = Comms()
	comms.start()
	time.sleep(2)
	while True:
		cmd = raw_input("Please enter a command: ")
		if cmd == 'go':
			comms.stop()
			comms.go()
		elif cmd == 'stop':
			comms.stop()
		elif cmd == 'goxy':
			comms.stop()
			fX = raw_input('from X: ')
			fY = raw_input('from Y: ')
			h = raw_input('Heading: ')
			tX = raw_input('to X: ')
			tY = raw_input('to Y: ')
			comms.goxy(fX, fY, h, tX, tY)
		elif cmd == 'turn':
	   		comms.stop()
			comms.turn(raw_input('Degrees: '), raw_input('Corrections: '))
		elif cmd == 'kick':
			comms.stop()
			comms.kick(10)
		elif cmd == 'hasball':
			pass
		elif cmd == 'reverse':
			comms.stop()
			dist = raw_input('Distance???: ')
			comms.reverse(dist)
		elif cmd == 'abort':
			comms.abort()
		elif cmd == 'grab':
			comms.stop()
			comms.grab(int(raw_input('1 to ungrab, 0 otherwise: ')))
		elif cmd == 'prepkick':
			pass
		elif cmd == 'receive':
			pass
		elif cmd == 'getball':
			pass
		elif cmd == 'reset':
			comms.reset()
		elif cmd == 'crash':
			comms = Comms()
			comms.start()
		elif cmd == 'getPos':
			print("Positions:", getPos())
		elif cmd == 'resetPos':
			print("Positions:", resetPos())
