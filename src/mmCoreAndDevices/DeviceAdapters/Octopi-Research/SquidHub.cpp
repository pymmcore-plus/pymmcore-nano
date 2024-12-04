#include "squid.h"
#include "crc8.h"

#ifdef WIN32
   #define WIN32_LEAN_AND_MEAN
   #include <windows.h>
#endif



const char* g_HubDeviceName = "SquidHub";

const char* g_AutoHome = "Home on startup";
const char* g_Yes = "Yes";
const char* g_No = "No";
const char* g_Acceleration = "Acceleration(mm/s^2)";
const char* g_Max_Velocity = "Max Velocity(mm/s)";


MODULE_API void InitializeModuleData() 
{
   RegisterDevice(g_HubDeviceName, MM::HubDevice, g_HubDeviceName);
   RegisterDevice(g_LEDShutterName, MM::ShutterDevice, "LEDs");
   RegisterDevice(g_XYStageName, MM::XYStageDevice, "XY-Stage");
   RegisterDevice(g_ZStageName, MM::StageDevice, "Z-Stage");
}


MODULE_API MM::Device* CreateDevice(const char* deviceName)
{

   if (strcmp(deviceName, g_HubDeviceName) == 0)
   {
      return new SquidHub();
   }
   else if (strcmp(deviceName, g_LEDShutterName) == 0)
   {
      return new SquidLEDShutter();
   }
   else if (strcmp(deviceName, g_XYStageName) == 0)
   {
      return new SquidXYStage();
   }
   else if (strcmp(deviceName, g_ZStageName) == 0)
   {
      return new SquidZStage();
   }

   // ...supplied name not recognized
   return 0;
}


MODULE_API void DeleteDevice(MM::Device* pDevice)
{
   delete pDevice;
}


SquidHub::SquidHub() :
   initialized_(false),
   autoHome_(false),
   monitoringThread_(0),
   xyStageDevice_(0),
   zStageDevice_(0),
   port_("Undefined"),
   cmdNrSend_(0),
   cmdNrReceived_(0)
{
   InitializeDefaultErrorMessages();

   CPropertyAction* pAct = new CPropertyAction(this, &SquidHub::OnPort);
   CreateProperty(MM::g_Keyword_Port, "Undefined", MM::String, false, pAct, true);
   x_ = 0l;
   y_ = 0l;
   z_ = 0l;
   xStageBusy_ = false;
   yStageBusy_ = false;
   zStageBusy_ = false;
   busy_ = false;

   pAct = new CPropertyAction(this, &SquidHub::OnAutoHome);
   CreateProperty(g_AutoHome, g_No, MM::String, false, pAct, true);
   AddAllowedValue(g_AutoHome, g_Yes);
   AddAllowedValue(g_AutoHome, g_No);
}


SquidHub::~SquidHub()   
{
   LogMessage("Destructor called");
}


void SquidHub::GetName(char* name) const
{
   CDeviceUtils::CopyLimitedString(name, g_HubDeviceName);
}


int SquidHub::Initialize() {
   Sleep(200);

   monitoringThread_ = new SquidMonitoringThread(*this->GetCoreCallback(), *this, true);
   monitoringThread_->Start();
   
   const unsigned cmdSize = 8;
   unsigned char cmd[cmdSize];
   cmd[0] = 0x00;
   cmd[1] = 255; // CMD_SET.RESET
   for (unsigned i = 2; i < cmdSize; i++) {
      cmd[i] = 0;
   }
   int ret = SendCommand(cmd, cmdSize);
   if (ret != DEVICE_OK) {
      return ret;
   }

   cmd[0] = 1; 
   cmd[1] = 254; // CMD_INITIALIZE_DRIVERS
   ret = SendCommand(cmd, cmdSize);
   if (ret != DEVICE_OK) {
      return ret;
   }

   if (autoHome_)
   {
      ret = Home();
      if (ret != DEVICE_OK) {
         return ret;
      }
   }

   initialized_ = true;

   return DEVICE_OK;
}


int SquidHub::Shutdown() {
   if (initialized_)
   {
      delete(monitoringThread_);
      initialized_ = false;
   }
   return DEVICE_OK;
}


bool SquidHub::Busy()
{
   return busy_;
   //return false;
}


bool SquidHub::SupportsDeviceDetection(void)
{
   return false;  // can implement this later

}


MM::DeviceDetectionStatus SquidHub::DetectDevice(void)
{
   // TODO
   return MM::CanCommunicate;  
}


int SquidHub::DetectInstalledDevices()
{
   if (MM::CanCommunicate == DetectDevice())
   {
      std::vector<std::string> peripherals;
      peripherals.clear();
      peripherals.push_back(g_LEDShutterName);
      peripherals.push_back(g_XYStageName);
      peripherals.push_back(g_ZStageName);
      for (size_t i = 0; i < peripherals.size(); i++)
      {
         MM::Device* pDev = ::CreateDevice(peripherals[i].c_str());
         if (pDev)
         {
            AddInstalledDevice(pDev);
         }
      }
   }

   return DEVICE_OK;
}



int SquidHub::OnPort(MM::PropertyBase* pProp, MM::ActionType eAct)
{
   if (eAct == MM::BeforeGet) {
      pProp->Set(port_.c_str());
   }
   else if (eAct == MM::AfterSet) {
      if (initialized_) {
         // revert}
         pProp->Set(port_.c_str());
         return ERR_PORT_CHANGE_FORBIDDEN;
      }
      // take this port.  TODO: should we check if this is a valid port?
      pProp->Get(port_);
   }

   return DEVICE_OK;
}


int SquidHub::assignXYStageDevice(SquidXYStage* xyStageDevice)
{
   xyStageDevice_ = xyStageDevice;
   return DEVICE_OK;
}


int SquidHub::assignZStageDevice(SquidZStage* zStageDevice)
{
   zStageDevice_ = zStageDevice;
   return DEVICE_OK;
}


int SquidHub::SendCommand(unsigned char* cmd, unsigned cmdSize)
{
   cmd[0] = ++cmdNrSend_;
   cmd[cmdSize - 1] = crc8ccitt(cmd, cmdSize - 1);
   if (true) {
      std::ostringstream os;
      os << "Sending message: ";
      for (unsigned int i = 0; i < cmdSize; i++) {
         os << std::hex << (unsigned int)cmd[i] << " ";
      }
      LogMessage(os.str().c_str(), false);
   }
   busy_ = true;
   status_ = IN_PROGRESS;
   return WriteToComPort(port_.c_str(), cmd, cmdSize);
}


void SquidHub::SetCmdNrReceived(uint8_t cmdNrReceived, uint8_t status) 
{
   if (cmdNrReceived != cmdNrReceived_ || status_ != status)
   {
      cmdNrReceived_ = cmdNrReceived;
      if (cmdNrReceived_ == cmdNrSend_)
      {
         status_ = status;
         busy_ = false;
      }
   }
}



/**
* Helper function to send Move or Move Relative command to relevant Stage
  MOVE_X = 0
  MOVE_Y = 1
  MOVE_Z = 2
  MOVE_THETA = 3
  MOVETO_X = 6
  MOVETO_Y = 7
  MOVETO_Z = 8
*/
int SquidHub::SendMoveCommand(const int command, long steps)
{
   const unsigned cmdSize = 8;
   unsigned char cmd[cmdSize];
   for (unsigned i = 0; i < cmdSize; i++) {
      cmd[i] = 0;
   }
   cmd[1] = (unsigned char)command;
   // TODO: Fix in case we are running on a Big Endian system
   cmd[2] = steps >> 24;
   cmd[3] = (steps >> 16) & 0xFF;
   cmd[4] = (steps >> 8) & 0xFF;
   cmd[5] = steps & 0xFF;

   if (command == CMD_MOVETO_X || command == CMD_MOVE_X)
      xStageBusy_ = true;
   else if (command == CMD_MOVETO_Y || command == CMD_MOVE_Y)
      yStageBusy_ = true;
   else if (command == CMD_MOVETO_Z || command == CMD_MOVE_Z)
      zStageBusy_ = true;

   return SendCommand(cmd, cmdSize);
}


/**
 * Velocity: max 65535/100 mm/s
 * Acceleration: max 65535/10 mm/s^2
 */
int SquidHub::SetMaxVelocityAndAcceleration(unsigned char axis, double maxVelocity, double acceleration)
{
   const unsigned cmdSize = 8;
   unsigned char cmd[cmdSize];
   for (unsigned i = 0; i < cmdSize; i++) {
      cmd[i] = 0;
   }
   cmd[1] = CMD_SET_MAX_VELOCITY_ACCELERATION;
   cmd[2] = axis;
   cmd[3] = uint16_t (maxVelocity * 100) >> 8;
   cmd[4] = uint16_t (maxVelocity * 100) & 0xff;
   cmd[5] = uint16_t (acceleration * 10) >> 8;
   cmd[6] = uint16_t (acceleration * 10) & 0xff;

   return SendCommand(cmd, cmdSize);
}


void SquidHub::GetPositionXYSteps(long& x, long& y)
{
   x = x_.load();
   y = y_.load();
}


void SquidHub::GetPositionZSteps(long& z)
{
   z = z_.load();
}


void SquidHub::SetPositionXSteps(long x)
{
   if (x_.load() != x)
   {
      xStageBusy_ = true;
      x_.store(x);
      if (xyStageDevice_ != 0)
         xyStageDevice_->Callback(x, y_.load());
   }
   else {
      xStageBusy_ = false;
   }
}


void SquidHub::SetPositionYSteps(long y)
{
   if (y_.load() != y)
   {
      yStageBusy_ = true;
      y_.store(y);
      if (xyStageDevice_ != 0)
         xyStageDevice_->Callback(x_.load(), y);
   }
   else {
      yStageBusy_ = false;
   }
}


void SquidHub::SetPositionZSteps(long z)
{
   if (z_.load() != z)
   {
      zStageBusy_ = true;
      z_.store(z);
      if (zStageDevice_ != 0)
         zStageDevice_->Callback(z_.load());
   }
   else {
      zStageBusy_ = false;
   }
}


bool SquidHub::XYStageBusy()
{
   return busy_ || (status_ != COMPLETED_WITHOUT_ERRORS) || xStageBusy_ || yStageBusy_;
}


bool SquidHub::ZStageBusy()
{
   return busy_ || (status_ != COMPLETED_WITHOUT_ERRORS) || zStageBusy_;
}


int SquidHub::OnAutoHome(MM::PropertyBase* pProp, MM::ActionType eAct)
{
   std::string response;
   if (eAct == MM::BeforeGet)
   {
      response = autoHome_ ? g_Yes : g_No;
      pProp->Set(response.c_str());
   }
   else if (eAct == MM::AfterSet)
   {
      pProp->Get(response);
      autoHome_ = response == g_Yes;
   }
   return DEVICE_OK;
}


int SquidHub::Home()
{
   const unsigned cmdSize = 8;
   unsigned char cmd[cmdSize];
   for (unsigned i = 0; i < cmdSize; i++) {
      cmd[i] = 0;
   }
   cmd[1] = CMD_HOME_OR_ZERO;
   cmd[2] = AXIS_Z;
   cmd[3] = int((STAGE_MOVEMENT_SIGN_Z + 1) / 2); // "move backward" if SIGN is 1, "move forward" if SIGN is - 1
   int ret = SendCommand(cmd, cmdSize);
   if (ret != DEVICE_OK)
      return ret;

   cmd[1] = CMD_HOME_OR_ZERO;
   cmd[2] = AXIS_XY;
   cmd[3] = int((STAGE_MOVEMENT_SIGN_X + 1) / 2); // "move backward" if SIGN is 1, "move forward" if SIGN is - 1
   cmd[4] = int((STAGE_MOVEMENT_SIGN_Y + 1) / 2); // "move backward" if SIGN is 1, "move forward" if SIGN is - 1
   return SendCommand(cmd, cmdSize);
}
