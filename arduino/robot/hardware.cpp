#include "hardware.h"
#include "global.h"

#include "SDPArduino.h"

#include <Wire.h>

void hardwareSetup() {

 //Initial set up for arduino connected to the power board.
 pinMode(2,INPUT);
 pinMode(3,OUTPUT);
 pinMode(4,INPUT);
 pinMode(5,OUTPUT);
 pinMode(6,OUTPUT);
 pinMode(7,INPUT);
 pinMode(8,OUTPUT);
 pinMode(9,OUTPUT);
 pinMode(10,INPUT);
 pinMode(11,INPUT);
 pinMode(12,INPUT);
 pinMode(13,INPUT);
 pinMode(A0,INPUT);
 pinMode(A1,INPUT);
 pinMode(A2,INPUT);
 pinMode(A3,INPUT);
 digitalWrite(8,HIGH); //Pin 8 must be high to turn the radio on!
 Serial.begin(115200); // Serial rate the radio is configured to.
 Wire.begin(); //Makes arduino master of the I2C line.
 Serial.println(F("Wire"));
 // CRASHES HERE
 greenMotorAllStop();
 Serial.println(F("mStop"));
 // ALSO CRASHES HERE
 resetMotorPositions();
 Serial.println(F("mRes"));
}

/* MOTORS */

long int positions[ROTARY_COUNT] = {0};

void updateMotorPositions() {
 // Request motor position deltas from rotary slave board

 Wire.requestFrom(ROTARY_SLAVE_ADDRESS, ROTARY_COUNT);

 // Update the recorded motor positions
 int i ;

 for (i = 0; i < ROTARY_COUNT; i++) {
   positions[i] += (int8_t) Wire.read();  // Must cast to signed 8-bit type
 }
}

void resetMotorPositions() {
 updateMotorPositions() ;
 memset(positions , 0 , sizeof(positions)) ;
}

void printMotorPositions() {
 print("Motor positions: ");
 int i ;
 for ( i = 0; i < ROTARY_COUNT; i++) {
   print(positions[i]);
   print(" ");
 }
 println("");
}

void greenMotorAllStop() {
  Serial.println(F("gas1"));
  //motorAllStop();
  for (int i=0; i < 5; i++) {
   Serial.println(i);
   motorStop(i);
  }
  Serial.println(F("gas2"));
}

// motorNo in range [1,8]
// motorPower in range [0,100]
// dir: 0 float, 1 fwd, 2 bckw, 3 brake
void greenMotorMove(int motorNum, int motorPower, enum MOTOR_DIR dir) {

 if (motorNum > 3 || motorNum < 0)
   return;

 if (motorPower < 0) {
   motorPower = abs(motorPower);
   if (dir == MOTOR_FWD) dir = MOTOR_BWD;
   else if (dir == MOTOR_BWD) dir = MOTOR_FWD;
 }
 if (motorPower > 100)
   motorPower = 100;

 //adapting the code base to work with the motor board we are using
 if(dir == MOTOR_FWD) motorForward(motorNum, motorPower);
 else if (dir == MOTOR_BWD) motorBackward(motorNum, motorPower);
 //float break and normal break are treated the same way
 else if (dir == MOTOR_FLOAT)
   motorStop(motorNum);
 else {
   motorForward(motorNum, 100);
   motorStop(motorNum);
 }

}


