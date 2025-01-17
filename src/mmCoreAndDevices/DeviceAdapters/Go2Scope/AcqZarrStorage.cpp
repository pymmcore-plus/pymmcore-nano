///////////////////////////////////////////////////////////////////////////////
// FILE:          AcqZarrStorage.cpp
// PROJECT:       Micro-Manager
// SUBSYSTEM:     DeviceAdapters
//-----------------------------------------------------------------------------
// DESCRIPTION:   Zarr writer based on the CZI acquire-zarr library
//
// AUTHOR:        Nenad Amodaj
//
// COPYRIGHT:     Nenad Amodaj, Chan Zuckerberg Initiative, 2024
//
// LICENSE:       This file is distributed under the BSD license.
//                License text is included with the source distribution.
//
//                This file is distributed in the hope that it will be useful,
//                but WITHOUT ANY WARRANTY; without even the implied warranty
//                of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
//
//                IN NO EVENT SHALL THE COPYRIGHT OWNER OR
//                CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
//                INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES.
//
// NOTE:          Storage Device development is supported in part by
//                Chan Zuckerberg Initiative (CZI)
// 
///////////////////////////////////////////////////////////////////////////////
#include "G2SStorage.h"
#include "AcqZarrStorage.h"
#include "acquire.zarr.h"
#include "nlohmann/json.hpp"
#include <random>
#include <sstream>
#include <iomanip>
#include <boost/filesystem.hpp>


using namespace std;


std::string generate_guid() {
   std::random_device rd;
   std::mt19937 gen(rd());
   std::uniform_int_distribution<> dis(0, 15);
   std::uniform_int_distribution<> dis2(8, 11);

   std::stringstream ss;
   ss << std::hex;

   for (int i = 0; i < 8; i++) {
      ss << dis(gen);
   }
   ss << "-";
   for (int i = 0; i < 4; i++) {
      ss << dis(gen);
   }
   ss << "-4";
   for (int i = 0; i < 3; i++) {
      ss << dis(gen);
   }
   ss << "-" << dis2(gen);
   for (int i = 0; i < 3; i++) {
      ss << dis(gen);
   }
   ss << "-";
   for (int i = 0; i < 12; i++) {
      ss << dis(gen);
   }

   return ss.str();
}

///////////////////////////////////////////////////////////////////////////////
// Zarr storage

AcqZarrStorage::AcqZarrStorage() :
   initialized(false), zarrStream(nullptr), currentImageNumber(0), dataType(MM::StorageDataType_UNKNOWN)
{
   InitializeDefaultErrorMessages();

	// set device specific error messages
   SetErrorText(ERR_ZARR, "Generic Zarr writer error. Check log for more information.");
   SetErrorText(ERR_INTERNAL, "Internal driver error, see log file for details");
   SetErrorText(ERR_ZARR_SETTINGS, "Error in creating Zarr settings.");
   SetErrorText(ERR_ZARR_NUMDIMS, "Number of Zarr dimensions is not valid.");
   SetErrorText(ERR_ZARR_STREAM_CREATE, "Error creating Zarr stream. See log for more info.");
   SetErrorText(ERR_ZARR_STREAM_CLOSE, "Error closing Zarr stream. See log for more info.");
   SetErrorText(ERR_ZARR_STREAM_LOAD, "Error opening an existing Zarr stream.");
   SetErrorText(ERR_ZARR_STREAM_APPEND, "Error appending image to Zarr stream.");
   SetErrorText(ERR_ZARR_STREAM_ACCESS, "Error accessing Zarr stream. See log for more info.");
   SetErrorText(ERR_ZARR_STREAM_LOAD, "Error opening an existing Zarr stream.");

   auto ver = Zarr_get_api_version();
                                                                             
   // create pre-initialization properties                                   
   // ------------------------------------
   //
                                                                          
   // Name                                                                   
   CreateProperty(MM::g_Keyword_Name, g_AcqZarrStorage, MM::String, true);
   //
   // Description
   ostringstream os;
   os << "Acquire Zarr Storage v" << ver;
   CreateProperty(MM::g_Keyword_Description, os.str().c_str(), MM::String, true);
}                                                                            
                                                                             
AcqZarrStorage::~AcqZarrStorage()                                                            
{                                                                            
   Shutdown();
} 

void AcqZarrStorage::GetName(char* Name) const
{
   CDeviceUtils::CopyLimitedString(Name, g_AcqZarrStorage);
}  

int AcqZarrStorage::Initialize()
{
   if (initialized)
      return DEVICE_OK;

	int ret(DEVICE_OK);

   UpdateStatus();

   initialized = true;
   return DEVICE_OK;
}

int AcqZarrStorage::Shutdown()
{
   if (initialized)
   {
      initialized = false;
   }
   destroyStream();

   return DEVICE_OK;
}

// Never busy because all commands block
bool AcqZarrStorage::Busy()
{
   return false;
}

/**
 * Creates Zarr dataset
 * 
 * \param path - parent directory of the dataset
 * \param name - name of the dataset (the actual name will follow the micro-manager convention for not overwriting)
 * \param numberOfDimensions - how many dimensions
 * \param shape - array of dimension sizes, from slow to fast. Y and X are always the last two.
 * \param pixType - pixel type
 * \param meta - JSON encoded string representing "summary" metadata. Can be empty.
 * \param handle - handle to the dataset.
 * \return 
 */
int AcqZarrStorage::Create(const char* path, const char* name, int numberOfDimensions, const int shape[], MM::StorageDataType pixType, const char* meta, char* handle)
{
   if (zarrStream)
   {
      LogMessage("Another stream is already open. Currently this device supports only one stream.");
      return ERR_ZARR_NUMDIMS;
   }

   if (numberOfDimensions < 3)
   {
      LogMessage("Number of dimensions is lower than 3.");
      return ERR_ZARR_NUMDIMS;
   }

   // Generate a unique path
   string savePrefix(name);
   string savePrefixTmp(name);
   string saveRoot(path);
   string dsName = string(path) + "/" + savePrefixTmp;
   int counter(1);
   while (boost::filesystem::exists(dsName))
   {
      savePrefixTmp = savePrefix + "_" + to_string(counter++);
      dsName = saveRoot + "/" + savePrefixTmp;
   }
   boost::system::error_code errCode;
   if (!boost::filesystem::create_directory(dsName, errCode))
      return ERR_FAILED_CREATING_FILE;

   ZarrStreamSettings settings = {};
   settings.store_path = dsName.c_str();
   settings.dimension_count = numberOfDimensions;
   // settings.multiscale = false;

   // set data type and convert to zarr
   int ztype = ConvertToZarrType(pixType);
   if (ztype == -1)
   {
      LogMessage("Pixel data type is not supported by Zarr writer " + pixType);
      return ERR_ZARR_SETTINGS;
   }
   settings.data_type = static_cast<ZarrDataType>(ztype);
   settings.version = ZarrVersion_2;

   // Allocate and set dimensions
   if (ZarrStreamSettings_create_dimension_array(&settings, numberOfDimensions) != ZarrStatusCode_Success)
   {
      LogMessage("Failed to allocate dimension array.");
      return ERR_ZARR_SETTINGS;
   }

   for (int i = 0; i < numberOfDimensions; ++i)
   {
      ZarrDimensionProperties& dim = settings.dimensions[i];
      ostringstream osd;
      if (i == numberOfDimensions - 2)
         osd << "y";
      else if (i == numberOfDimensions - 1)
         osd << "x";
      else
         osd << "dim-" << i;

      string dimName = osd.str();
      dim.name = dimName.c_str();
      dim.array_size_px = shape[i];
      dim.chunk_size_px = (i >= numberOfDimensions - 2) ? shape[i] : 1;
      dim.shard_size_chunks = 1;
      dim.type = (i >= numberOfDimensions - 2) ? ZarrDimensionType_Space : ZarrDimensionType_Other;
   }

   // Set custom metadata
   if (meta && strlen(meta) > 0)
   {
      settings.custom_metadata = meta;
   }

   // Create the Zarr stream
   zarrStream = ZarrStream_create(&settings);
   if (zarrStream == nullptr)
   {
      LogMessage("Failed creating Zarr stream: " + dsName);
      ZarrStreamSettings_destroy_dimension_array(&settings);
      return ERR_ZARR_STREAM_CREATE;
   }

   // Finalize
   dataType = pixType;
   streamHandle = generate_guid();
   streamDimensions.clear();
   for (int i = 0; i < numberOfDimensions; i++)
   {
      streamDimensions.push_back(shape[i]);
   }
   // TODO: allow many streams

   currentImageNumber = 0;
   strncpy(handle, streamHandle.c_str(), MM::MaxStrLength);

   // Clean up
   ZarrStreamSettings_destroy_dimension_array(&settings);
   LogMessage("Created Zarr stream: " + dsName + " with handle: " + streamHandle + " and number of dimensions: " + to_string(numberOfDimensions));

   streamPath = dsName;

   return DEVICE_OK;
}

int AcqZarrStorage::ConfigureDimension(const char* handle, int dimension, const char* name, const char* meaning)
{
   return DEVICE_OK;
}

int AcqZarrStorage::ConfigureCoordinate(const char* handle, int dimension, int coordinate, const char* name)
{
   return DEVICE_OK;
}

int AcqZarrStorage::Close(const char* handle)
{
   if (zarrStream == nullptr)
   {
      LogMessage("No stream is currently open.");
      return ERR_ZARR_STREAM_CLOSE;
   }
   if (streamHandle.compare(handle) != 0)
   {
      LogMessage("Handle is not valid.");
      return ERR_ZARR_STREAM_CLOSE;
   }

   streamPath.clear();
   destroyStream();

   return DEVICE_OK;
}

int AcqZarrStorage::Load(const char* path, char* handle)
{
   return DEVICE_NOT_YET_IMPLEMENTED;
}

int AcqZarrStorage::GetShape(const char* handle, int shape[])
{
   if (zarrStream == nullptr)
   {
      LogMessage("No stream is currently open.");
      return ERR_ZARR_STREAM_ACCESS;
   }
   if (streamHandle.compare(handle) != 0)
   {
      LogMessage("Handle is not valid.");
      return ERR_ZARR_STREAM_ACCESS;
   }

   int i(0);
   for (auto d : streamDimensions) shape[i++] = d;

   return DEVICE_OK;
}

int AcqZarrStorage::Delete(char* handle)
{
   return DEVICE_NOT_YET_IMPLEMENTED;
}

int AcqZarrStorage::List(const char* path, char** listOfDatasets, int maxItems, int maxItemLength)
{
   return DEVICE_NOT_YET_IMPLEMENTED;
}

int AcqZarrStorage::AddImage(const char* handle, int sizeInBytes, unsigned char* pixels, int coordinates[], int numCoordinates, const char* imageMeta)
{
   if (zarrStream == nullptr)
   {
      LogMessage("No stream is currently open.");
      return ERR_ZARR_STREAM_ACCESS;
   }
   if (streamHandle.compare(handle) != 0)
   {
      LogMessage("Handle is not valid.");
      return ERR_ZARR_STREAM_ACCESS;
   }

   if (streamDimensions[streamDimensions.size() - 2] * streamDimensions[streamDimensions.size() - 1] * MM::GetPixelDataSizeInBytes(dataType) != sizeInBytes)
   {
      LogMessage("Stream dimensions do not match image size");
      return ERR_ZARR_STREAM_APPEND;
   }

   size_t bytesIn(sizeInBytes);
   size_t bytesOut(0);
   ZarrStatusCode status = ZarrStream_append(zarrStream, pixels, bytesIn, &bytesOut);
   if (status != ZarrStatusCode_Success)
   {
      LogMessage(getErrorMessage(status));
      return ERR_ZARR_STREAM_APPEND;
   }

   if (bytesOut != bytesIn)
   {
      ostringstream os;
      os << "Bytes in " << bytesIn << " does not match bytes out " << bytesOut;
      LogMessage(os.str());
      return ERR_ZARR_STREAM_APPEND;
   }
   currentImageNumber++;

   return DEVICE_OK;
}

int AcqZarrStorage::GetSummaryMeta(const char* handle, char* meta, int bufSize)
{
   if (zarrStream == nullptr)
   {
      LogMessage("No stream is currently open.");
      return ERR_ZARR_STREAM_ACCESS;
   }
   if (streamHandle.compare(handle) != 0)
   {
      LogMessage("Handle is not valid.");
      return ERR_ZARR_STREAM_ACCESS;
   }

   if (bufSize > 0)
      meta[0] = 0;

   return 0;
}

int AcqZarrStorage::GetImageMeta(const char* handle, int coordinates[], int numCoordinates, char* meta, int bufSize)
{
   if (zarrStream == nullptr)
   {
      LogMessage("No stream is currently open.");
      return ERR_ZARR_STREAM_ACCESS;
   }
   if (streamHandle.compare(handle) != 0)
   {
      LogMessage("Handle is not valid.");
      return ERR_ZARR_STREAM_ACCESS;
   }

   if (bufSize > 0)
      meta[0] = 0;

   return 0;
}

const unsigned char* AcqZarrStorage::GetImage(const char* handle, int coordinates[], int numCoordinates)
{
   if (zarrStream == nullptr)
   {
      LogMessage("No stream is currently open.");
      return nullptr;
   }
   if (streamHandle.compare(handle) != 0)
   {
      LogMessage("Handle is not valid.");
      return nullptr;
   }

   return nullptr;
}

int AcqZarrStorage::GetNumberOfDimensions(const char* handle, int& numDimensions)
{
   if (streamHandle.compare(handle) != 0)
   {
      LogMessage("Handle is not valid.");
      return ERR_ZARR_STREAM_ACCESS;
   }
   return streamDimensions.size();
}

int AcqZarrStorage::GetDimension(const char* handle, int dimension, char* name, int nameLength, char* meaning, int meaningLength)
{
   return DEVICE_NOT_YET_IMPLEMENTED;
}

int AcqZarrStorage::GetCoordinate(const char* handle, int dimension, int coordinate, char* name, int nameLength)
{
   return DEVICE_NOT_YET_IMPLEMENTED;
}

bool AcqZarrStorage::IsOpen(const char* handle)
{
   if (streamHandle.compare(handle) != 0)
   {
      return false;
   }
   return true;
}

int AcqZarrStorage::GetPath(const char* handle, char* path, int maxPathLength)
{
   return 0;
}

std::string AcqZarrStorage::getErrorMessage(int code)
{
   return std::string(Zarr_get_status_message((ZarrStatusCode)code));
}

void AcqZarrStorage::destroyStream()
{
   if (zarrStream)
   {
      ZarrStream_destroy(zarrStream);
      zarrStream = nullptr;
      streamHandle = "";
   }
}

int AcqZarrStorage::ConvertToZarrType(MM::StorageDataType type)
{
   ZarrDataType ztype;
   switch (type)
   {
      case MM::StorageDataType_GRAY8:
         ztype = ZarrDataType_uint8;
      break;

      case MM::StorageDataType_GRAY16:
         ztype = ZarrDataType_int16;  // why is there no uint16?
      break;

      default:
         return -1;
   }
   return (int)ztype;
}


///////////////////////////////////////////////////////////////////////////////
// Action handlers
///////////////////////////////////////////////////////////////////////////////

