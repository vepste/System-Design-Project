/*	Author = helscream (Omer Ikram ul Haq) 
	Date = 2014-05-11
	Website: http://hobbylogs.me.pn/?p=17
        Location: Pakistan
	Ver: 0.1 beta
*/

#ifndef compass
  #define compass
  #include "compass.h"
  
  extern float bearing;
  extern float compass_x_scalled;
  extern float compass_y_scalled;
  extern float compass_z_scalled;
  
  extern float compass_x_offset, compass_y_offset, compass_z_offset;
  extern float compass_x_gainError,compass_y_gainError,compass_z_gainError;

  void getCompass();
  void compass_read_XYZdata();
  void compass_offset_calibration(int select);
  void compass_init(int gain);
  void compass_scalled_reading();
  void compass_heading(); 
  
#endif
