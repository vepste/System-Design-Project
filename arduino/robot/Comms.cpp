#include "Comms.h"

#include "GoInstruction.h"
#include "ReverseInstruction.h"
#include "GoXYInstruction.h"
#include "TurnInstruction.h"
#include "PauseInstruction.h"
#include "GetBallInstruction.h"
#include "KickInstruction.h"
#include "GrabInstruction.h"
#include "ReceiveInstruction.h"
#include "compass.h"
#include "hardware.h"
// #include "PrepKickInstruction.h"
// #include "PenDefInstruction.h"


#define ID_BYTES 2
#define OPCODE_BYTES 1
#define HASH_BYTES 2

/* Static Methods */

int noParamsBytesForOpcode(Opcode opcode) {
  // note: not number of params, but number of bytes for params
  switch (opcode) {
    case RESET:     return 0;
    case STOP:      return 0;
    case UPDATEWM:  return 10; // [4]unsigned, [2]signed, [2]signed, [2]signed
    case GO:        return 0;
    case GOXY:      return 10; // [2]signed, [2]signed, [2]signed, [2]signed, [2]signed
    case GETBALL:   return 10; // [2]signed, [2]signed, [2]signed, [2]signed, [2]signed
    case TURN:      return 3;  // [2]signed, [1]unsigned
    case GRAB:      return 1;  // [1]unsigned
    case RECEIVE:   return 4;  // [4]unsigned
    case PREPKICK:  return 1;  // [1]unsigned
    case KICK:      return 1;  // [1]unsigned
    case REVERSE:   return 2;  // [2]unsigned
    case ABORT:     return 0;
    case HASBALL:   return 0;
    case RETARG:    return 6;  // [2]unsigned, [2]signed, [2]signed
    case GETPOS:    return 0;
    case RESETPOS:  return 0;
    case GETCOMPASS:return 0;
    default:        return 0;
  }
}

Comms::Comms() {
  this->expectedMessageID = 2;
  this->clearSoftwareBuffer();
  this->clearSerialBuffer();
}

void Comms::readSerial() {

  /*
   Read bytes in the Serial buffer into this->buffer
   At each byte, check if it completes an instruction
   If so, interprets it and resets buffer
  */
  while (Serial.available() > 0) {

    // read byte and add it to buffer
    byte inByte = Serial.read();
    // software buffer overflow
    if (this->bufferPos >= BUFFER_SIZE) {
      Serial.println(F("Error: Comms software buffer overflow."));
      this->clearSoftwareBuffer();
      this->clearSerialBuffer();
      return;
    }

    // append byte to buffer
    this->buffer[this->bufferPos] = inByte;
    this->bufferPos++;
    // check to see if a whole command is contained within buffer
    this->checkForCompleteCommand();
    //}
  }
}

/*
 Resets expectedMessageID
 Necessary when the PC-side system restarts but we haven't
 Set to 2 as opposed to 1 because the RESET command had ID 1
*/
void Comms::resetMessID() {
  this->expectedMessageID = 2;
  //this->maxIDSuccessPCToArd = 1;
}

/*
 clears any bytes on the software buffer belonging to this class
*/
void Comms::clearSoftwareBuffer() {
  for (int i = 0 ; i < this->bufferPos ; i++)
    this->buffer[i] = 0;
  this->bufferPos = 0;
}

/*
 clears any bytes on the hardware serial buffer
 only call when error discovered
*/
void Comms::clearSerialBuffer() {
  while(Serial.available() > 0)
    Serial.read();
}

/*
 called whenever a new byte is added to buffer
 check if we have enough bytes for a whole command
 */
void Comms::checkForCompleteCommand() {
  Command cmd;
  parseResult result = cmd.commandFromBytes(this->buffer, this->bufferPos);

  //Serial.println(buffer[bufferPos]);

  if (result == TOO_SHORT)
    return;
  else if (result == INVALID) {
    Serial.println(F("Error: Comms parse error"));
    this->clearSoftwareBuffer();
    this->clearSerialBuffer();
    return;
  }

  if (this->validateNewCommand(cmd)) {
    // update maxIDSuccessPCToArd, tell PC success and execute instruction
    //this->maxIDSuccessPCToArd = cmd.id;
    // anticipate next command, if the command is a repeat, we have already resent the success message
    if (cmd.id == this->expectedMessageID) {
      this->expectedMessageID = cmd.id + 1;
      this->respondSuccess();
      cmd.instantiateInstruction();
    }
  } else {
    // tell the PC there was an error and clear the hardware buffer
    this->respondError();
    this->clearSerialBuffer();
  }

  // clear the software buffer regardless of success
  // (we never read more than we absolutely need for a command)
  this->clearSoftwareBuffer();
}

/*
 ID must be expectedID
 Hash must add up
 Opcode must be valid
*/
bool Comms::validateNewCommand(Command c) {
  
  if (c.id == 1 && c.opcode == RESET)
    return true;

  if (c.id < this->expectedMessageID) {
    Serial.print(F("$SUC&"));
    Serial.print(c.id);
    Serial.println(F(";"));
    return true;
  }
  
  if (c.id != this->expectedMessageID) {
    Serial.println(F("ERRid"));
    Serial.println(c.id);
    Serial.println(this->expectedMessageID);
    return false;
  }


  if (!c.hashAddsUp()) {
    Serial.println(F("ERRhash"));
    Serial.println(c.hash);
    Serial.println(c.computeHash());
    return false;
  }

  if (!c.opcodeValid()) {
    Serial.println(F("ERRopcode"));
    Serial.println(c.opcode);
    return false;
  }

  return true;
}

/*
 Sends command to PC to say we've reset and expect IDs to begin at 1
*/
void Comms::sendArdReset() {
  Serial.print(F("$ARDRESET;"));
}

/*
 Respond Error and provide the next expected message ID
*/
void Comms::respondError() {
  Serial.print(F("$ERR&"));
  Serial.print((this->expectedMessageID));
  Serial.println(F(";"));
}

/*
 Respond Success and provide the last successfully received message ID
*/
void Comms::respondSuccess() {
  Serial.print(F("$SUC&"));
  Serial.print((this->expectedMessageID-1));
  Serial.println(F(";"));
}

/*
 Sends command to PC to say we've completed a specific instruction with success=yes/no
*/
void Comms::sendInstructionCompleteParam(int cmdID, bool success) {
  if (cmdID < 0)
    return;
  Serial.print(F("$COMP&"));
  Serial.print(cmdID);
  Serial.print(F("&"));
  Serial.print(success);
  Serial.print(F(";"));
}

void Comms::sendInstructionValueParam(int cmdID, int val) {
  if (cmdID < 0)
    return;
  Serial.print(F("$COMP&"));
  Serial.print(cmdID);
  Serial.print(F("&"));
  Serial.print(val);
  Serial.print(F(";"));
}

/*
 Sends command to PC to say we've completed a specific instruction
*/
void Comms::sendInstructionComplete(int cmdID) {
  if (cmdID < 0)
    return;
  Serial.print(F("$COMP&"));
  Serial.print(cmdID);
  Serial.print(F(";"));
}

/* Command */

Command::Command() {
  this->id = 0;
  this->opcode = INVALID_OP;
  this->hash = 0;
}

/*
 Constructor method for command from PC to Arduino.
 Returns false if not enough bytes yet
 Otherwise, returns true and sets relevant field of Command
*/
parseResult Command::commandFromBytes(byte buffer[], int bufferPos) {

  // must have at least ID, opcode, hash
  if (bufferPos < ID_BYTES + OPCODE_BYTES + HASH_BYTES)
    return TOO_SHORT;

  this->id = buffer[1] | buffer[0] << 8;
  this->opcode = static_cast<Opcode>(buffer[2]);

  if (!this->opcodeValid()) {
    //Serial.println(this->opcode);
    return INVALID;
  }

  // all params 2 bytes
  int paramBytes = noParamsBytesForOpcode(this->opcode);

  // now we know params length, do we have all required bytes to interpret command?
  if (bufferPos < ID_BYTES + OPCODE_BYTES + HASH_BYTES + paramBytes)
    return TOO_SHORT;

  // params is a byte array of size 2n where n is number of params
  for (int i = 0 ; i <  paramBytes ; i++)
    this->params[i] = buffer[ID_BYTES + OPCODE_BYTES+i];

  // hash is last 2 bytes of instruction
  this->hash = buffer[1+ID_BYTES + OPCODE_BYTES+paramBytes] | buffer[ID_BYTES + OPCODE_BYTES+paramBytes] << 8;

  return SUCCESS;
}

bool Command::hashAddsUp() {
  return this->computeHash() == this->hash;
}

bool Command::opcodeValid() {
   return (this->opcode >= MIN_OPCODE && this->opcode <= MAX_OPCODE);
}

unsigned int Command::computeHash() {

  // hash computed by summing individual bytes of id, opcode and params
  unsigned int total = 0;

  total += ((this->id & 0xFF00) >> 8);
  total += (this->id & 0x00FF);

  total += static_cast<int>(this->opcode);

  for (int i = 0 ; i < noParamsBytesForOpcode(this->opcode) ; i++)
    total += this->params[i];

  return total;
}

/*
 Given a well-formed command, this method instantiates an Instruction
 or calls necessary methods
*/
void Command::instantiateInstruction() {
  switch (this->opcode) {
    case RESET: {
      comms.resetMessID();
      comms.sendArdReset();
      resetWorldModel();
      deleteAllInstructions();
      break;
    }
    case STOP:
      deleteAllInstructions();
      break;
    case UPDATEWM:
      updateWorldModel(this->params);
      break;
    case GO:
      GoInstruction::initFromCommand(*this);
      break;
    case GOXY:
      GoXYInstruction::initFromCommand(*this);
      break;
    case GETBALL:
      GetBallInstruction::initFromCommand(*this);
      break;
    case TURN:
      TurnInstruction::initFromCommand(*this);
      break;
    case KICK:
      KickInstruction::initFromCommand(*this);
      break;
    case REVERSE:
      ReverseInstruction::initFromCommand(*this);
      break;
    case GRAB:
      GrabInstruction::initFromCommand(*this);
      break;
    case GETPOS:
      updateMotorPositions();
      printMotorPositions();
      break;
    case RESETPOS:
      resetMotorPositions();
      printMotorPositions();
      break;
    case GETCOMPASS:
      getCompass();
      break;
    case HASBALL:
      if (IRSensor.getDistanceCentimeter() < 8) {
        Serial.println(F("$BALL;"));
      }
      break;
    default:
      Serial.println(F("Error: opcode not defined"));
      break;
  }
}
