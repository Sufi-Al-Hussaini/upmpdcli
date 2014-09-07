/* Copyright (C) 2014 J.F.Dockes
 *       This program is free software; you can redistribute it and/or modify
 *       it under the terms of the GNU General Public License as published by
 *       the Free Software Foundation; either version 2 of the License, or
 *       (at your option) any later version.
 *
 *       This program is distributed in the hope that it will be useful,
 *       but WITHOUT ANY WARRANTY; without even the implied warranty of
 *       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *       GNU General Public License for more details.
 *
 *       You should have received a copy of the GNU General Public License
 *       along with this program; if not, write to the
 *       Free Software Foundation, Inc.,
 *       59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
 */
#ifndef _AVTRANSPORT_HXX_INCLUDED_
#define _AVTRANSPORT_HXX_INCLUDED_

#include <string>
#include <memory>

#include "libupnpp/control/service.hxx"

namespace UPnPClient {

class AVTransport;
typedef std::shared_ptr<AVTransport> AVTH;

/**
 * AVTransport Service client class.
 *
 */
class AVTransport : public Service {
public:

    /** Construct by copying data from device and service objects.
     *
     */
    AVTransport(const UPnPDeviceDesc& device,
                const UPnPServiceDesc& service)
        : Service(device, service)
        {
            registerCallback();
        }

    AVTransport() {}

    enum TransportState {Unknown, Stopped, Playing, Transitioning, 
                         PausedPlayback, PausedRecording, Recording, 
                         NoMediaPresent};
    enum TransportStatus {TPS_Unknown, TPS_Ok, TPS_Error};
    enum PlayMode {PM_Unknown, PM_Normal, PM_Shuffle, PM_RepeatOne, 
                   PM_RepeatAll, PM_Random, PM_Direct1};


    int setAVTransportURI(const string& uri, const string& metadata,
                          int instanceID=0)
    {
        return setURI(uri, metadata, instanceID, false);
    }

    int setNextAVTransportURI(const string& uri, const string& metadata,
                              int instanceID=0)
    {
        return setURI(uri, metadata, instanceID, true);
    }

    int setPlayMode(PlayMode pm, int instanceID=0);
    struct MediaInfo {
        int nrtracks;
        int mduration; // seconds
        std::string cururi;
        UPnPDirObject curmeta;
        std::string nexturi;
        UPnPDirObject nextmeta;
        std::string pbstoragemed;
        std::string rcstoragemed;
        std::string ws;
    };
    int getMediaInfo(MediaInfo& info, int instanceID=0);

    struct TransportInfo {
        TransportState tpstate;
        TransportStatus tpstatus;
        int curspeed;
    };
    int getTransportInfo(TransportInfo& info, int instanceID=0);

    struct PositionInfo {
        int track;
        int trackduration; // secs
        UPnPDirObject trackmeta;
        std::string trackuri;
        int reltime;
        int abstime;
        int relcount;
        int abscount;
    };
    int getPositionInfo(PositionInfo& info, int instanceID=0);

    struct DeviceCapabilities {
        std::string playmedia;
        std::string recmedia;
        std::string recqualitymodes;
    };
    int getDeviceCapabilities(DeviceCapabilities& info, int instanceID=0);

    struct TransportSettings {
        PlayMode playmode;
        std::string recqualitymode;
    };
    int getTransportSettings(TransportSettings& info, int instanceID=0);

    int stop(int instanceID=0);
    int pause(int instanceID=0);
    int play(int speed = 1, int instanceID = 0);
    enum SeekMode {SEEK_TRACK_NR, SEEK_ABS_TIME,
                   SEEK_REL_TIME, SEEK_ABS_COUNT,
                   SEEK_REL_COUNT, SEEK_CHANNEL_FREQ, 
                   SEEK_TAPE_INDEX, SEEK_FRAME};
    // Target in seconds for times.
    int seek(SeekMode mode, int target, int instanceID=0); 

    // These are for multitrack medium like a CD. No meaning for electronic
    // tracks where set(next)AVTransportURI() is used
    int next(int instanceID=0);
    int previous(int instanceID=0);

    int getCurrentTransportActions(std::string& actions, int instanceID=0);

    /** Test service type from discovery message */
    static bool isAVTService(const std::string& st);

protected:
    static const string SType;
    int setURI(const string& uri, const string& metadata,
               int instanceID, bool next);
private:
    void evtCallback(const std::unordered_map<std::string, std::string>&);
    void registerCallback();

};

} // namespace UPnPClient

#endif /* _AVTRANSPORT_HXX_INCLUDED_ */
