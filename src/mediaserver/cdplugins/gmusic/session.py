# Copyright (C) 2016 J.F.Dockes
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the
#   Free Software Foundation, Inc.,
#   59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
from __future__ import print_function

import sys
import json
import datetime
import time
from upmplgmodels import Artist, Album, Track, Playlist, SearchResult, \
     Category, Genre
from gmusicapi import Mobileclient

class Session(object):
    def __init__(self):
        self.api = None
        self.user = None
        self.lib_albums = {}
        self.lib_artists = {}
        self.lib_tracks = {}
        self.lib_updatetime = 0
        self.sitdata = []
        self.sitbyid = {}
        self.sitdataupdtime = 0
        
    def dmpdata(self, who, data):
        print("%s: %s" % (who, json.dumps(data, indent=4)), file=sys.stderr)
        
    def login(self, username, password, deviceid=None):
        self.api = Mobileclient(debug_logging=False)

        if deviceid is None:
            logged_in = self.api.login(username, password,
                                       Mobileclient.FROM_MAC_ADDRESS)
        else:
            logged_in = self.api.login(username, password, deviceid)

        #print("Logged in: %s" % logged_in)
        #data = self.api.get_registered_devices()
        #print("registered: %s" % data)
        #isauth = self.api.is_authenticated()
        #print("Auth ok: %s" % isauth)
        return logged_in

    def _get_user_library(self):
        now = time.time()
        if now - self.lib_updatetime < 300:
            return
        data = self.api.get_all_songs()
        #self.dmpdata("all_songs", data)
        self.lib_updatetime = now
        tracks = [_parse_track(t) for t in data]
        self.lib_tracks = dict([(t.id, t) for t in tracks])
        for track in tracks:
            # We would like to use the album id here, but gmusic
            # associates the tracks with any compilations after
            # uploading (does not use the metadata apparently), so
            # that we can't (we would end up with multiple
            # albums). OTOH, the album name is correct (so seems to
            # come from the metadata). What we should do is test the
            # album ids for one album with a matching title, but we're
            # not sure to succeed. So at this point, the album id we
            # end up storing could be for a different albums, and we
            # should have a special library-local get_album_tracks
            self.lib_albums[track.album.name] = track.album
            self.lib_artists[track.artist.id] = track.artist
            
    def get_user_albums(self):
        self._get_user_library()
        return self.lib_albums.values()

    def get_user_artists(self):
        self._get_user_library()
        return self.lib_artists.values()

    def get_user_playlists(self):
        pldata = self.api.get_all_playlists()
        #self.dmpdata("playlists", pldata)
        return [_parse_playlist(pl) for pl in pldata]

    def get_user_playlist_tracks(self, playlist_id):
        self._get_user_library()
        data = self.api.get_all_user_playlist_contents()
        #self.dmpdata("user_playlist_content", data)
        trkl = [item['tracks']
                for item in data if item['id'] == playlist_id]
        if not trkl:
            return []
        try:
            return [self.lib_tracks[track['trackId']] for track in trkl[0]]
        except:
            return []
        
    def create_station_for_genre(self, genre_id):
        id = self.api.create_station("station"+genre_id, genre_id=genre_id)
        return id

    def get_user_stations(self):
        data = self.api.get_all_stations()
        # parse_playlist works fine for stations
        stations = [_parse_playlist(d) for d in data]
        return stations

    def delete_user_station(self, id):
        self.api.delete_stations(id)

    # not working right now
    def listen_now(self):
        print("api.get_listen_now_items()", file=sys.stderr)
        ret = {'albums' : [], 'stations' : []}
        try:
            data = self.api.get_listen_now_items()
        except Exception as err:
            print("api.get_listen_now_items failed: %s" % err, file=sys.stderr)
            data = None

        # listen_now entries are not like normal albums or stations,
        # and need special parsing. I could not make obvious sense of
        # the station-like listen_now entries, so left them aside for
        # now. Maybe should use create_station on the artist id?
        if data:
            ret['albums'] = [_parse_ln_album(a['album']) \
                             for a in data if 'album' in a]
            #ret['stations'] = [_parse_ln_station(d['radio_station']) \
            #                   for d in data if 'radio_station' in d]
        else:
            print("listen_now: no items returned !", file=sys.stderr)
        print("get_listen_now_items: returning %d albums and %d stations" %\
              (len(ret['albums']), len(ret['stations'])), file=sys.stderr)
        return ret

    def get_situation_content(self, id = None):
        ret = {'situations' : [], 'stations' : []}
        now = time.time()
        if id is None and now - self.sitdataupdtime > 300:
            self.sitbyid = {}
            self.sitdata = self.api.get_listen_now_situations()
            self.sitdataupdtime = now

        # Root is special, it's a list of situations
        if id is None:
            ret['situations'] = [self._parse_situation(s) \
                                 for s in self.sitdata]
            return ret
        
        # not root
        if id not in self.sitbyid:
            print("get_situation_content: %s unknown" % id, file=sys.stderr)
            return ret

        situation = self.sitbyid[id]
        #self.dmpdata("situation", situation)
        if 'situations' in situation:
            ret['situations'] = [self._parse_situation(s) \
                                 for s in situation['situations']]
        if 'stations' in situation:
            ret['stations'] = [_parse_situation_station(s) \
                               for s in situation['stations']]

        return ret

    def _parse_situation(self, data):
        self.sitbyid[data['id']] = data
        return Playlist(id=data['id'], name=data['title'])
        
    def create_curated_and_get_tracks(self, id):
        sid = self.api.create_station("station"+id, curated_station_id=id)
        print("create_curated: sid %s"%sid, file=sys.stderr)
        tracks = [_parse_track(t) for t in self.api.get_station_tracks(sid)]
        #print("curated tracks: %s"%tracks, file=sys.stderr)
        self.api.delete_stations(sid)
        return tracks
    
    def get_station_tracks(self, id):
        return [_parse_track(t) for t in self.api.get_station_tracks(id)]
    
    def get_media_url(self, song_id, quality=u'med'):
        url = self.api.get_stream_url(song_id, quality=quality)
        print("get_media_url got: %s" % url, file=sys.stderr)
        return url

    def get_album_tracks(self, album_id):
        data = self.api.get_album_info(album_id, include_tracks=True)
        album = _parse_album(data)
        return [_parse_track(t, album) for t in data['tracks']]

    def get_promoted_tracks(self):
        data = self.api.get_promoted_songs()
        #self.dmpdata("promoted_tracks", data)
        return [_parse_track(t) for t in data]

    def get_genres(self, parent=None):
        data = self.api.get_genres(parent_genre_id=parent)
        return [_parse_genre(g) for g in data]
                
    def get_artist_info(self, artist_id, doRelated=False):
        ret = {"albums" : [], "toptracks" : [], "related" : []} 
        # Happens,some library tracks have no artistId entry
        if artist_id is None or artist_id == 'None':
            print("get_artist_albums: artist_id is None", file=sys.stderr)
            return ret
        else:
            print("get_artist_albums: artist_id %s" % artist_id, file=sys.stderr)

        maxrel = 20 if doRelated else 0
        maxtop = 0 if doRelated else 10
        incalbs = False if doRelated else True
        data = self.api.get_artist_info(artist_id, include_albums=incalbs,
                                        max_top_tracks=maxtop,
                                        max_rel_artist=maxrel)
        #self.dmpdata("artist_info", data)
        if 'albums' in data:
            ret["albums"] = [_parse_album(alb) for alb in data['albums']]
        if 'topTracks' in data:
            ret["toptracks"] = [_parse_track(t) for t in data['topTracks']]
        if 'related_artists' in data:
            ret["related"] = [_parse_artist(a) for a in data['related_artists']]
        return ret

    def get_artist_related(self, artist_id):
        data = self.get_artist_info(artist_id, doRelated=True)
        return data["related"]
    
    def search(self, query):
        data = self.api.search(query, max_results=50)
        #self.dmpdata("Search", data)

        tr = [_parse_track(i['track']) for i in data['song_hits']]
        print("track ok", file=sys.stderr)
        ar = [_parse_artist(i['artist']) for i in data['artist_hits']]
        print("artist ok", file=sys.stderr)
        al = [_parse_album(i['album']) for i in data['album_hits']]
        print("album ok", file=sys.stderr)
        #self.dmpdata("Search playlists", data['playlist_hits'])
        try:
            pl = [_parse_splaylist(i) for i in data['playlist_hits']]
        except:
            pl = []
        print("playlist ok", file=sys.stderr)
        return SearchResult(artists=ar, albums=al, playlists=pl, tracks=tr)



def entryOrUnknown(data, name, default="Unknown"):
    return data[name] if name in data else default


def _parse_artist(data):
    return Artist(id=data['artistId'], name=data['name'])

def _parse_genre(data):
    return Genre(id=data['id'], name=data['name'])

def _parse_playlist(data):
    return Playlist(id=data['id'], name=data['name'])

def _parse_splaylist(data):
    return Playlist(id=data['playlist']['shareToken'],
                    name=data['playlist']['name'])

def _parse_situation_station(data):
    return Playlist(id=data['seed']['curatedStationId'], name=data['name'])


def _parse_track(data, album=None):
    artist_name = entryOrUnknown(data, 'artist')
    albartist_name = entryOrUnknown(data, 'albartistAlbum', None)

    artistid = data["artistId"][0] if "artistId" in data else None
    artist = Artist(id=artistid, name = artist_name)
    albartist = Artist(id=artistid, name=albartist_name) if \
                albartist_name is not None else artist
    albid = entryOrUnknown(data, 'albumId', None)
    
    if album is None:
        #alb_artist = data['albumArtist'] if 'albumArtist' in data else ""
        alb_art= data['albumArtRef'][0]["url"] if 'albumArtRef' in data else ""
        alb_tt = entryOrUnknown(data, 'album')
        album = Album(id=albid, name=alb_tt, image=alb_art, artist=artist)

    kwargs = {
        'id': data['id'] if 'id' in data else data['nid'],
        'name': data['title'],
        'duration': int(data['durationMillis'])/1000,
        'track_num': data['trackNumber'],
        'disc_num': data['discNumber'],
        'artist': artist,
        'album': album,
        #'artists': artists,
    }
    if 'genre' in data:
        kwargs['genre'] = data['genre'] 
    
    return Track(**kwargs)


def _parse_ln_album(data):
    artist = Artist(id=data['artist_metajam_id'], name=data['artist_name'])
    kwargs = {
        'id': data['id']['metajamCompactKey'],
        'name' : data['id']['title'],
        'artist' : artist,
    }
    if 'images' in data:
        kwargs['image'] = data['images'][0]['url']

    return Album(**kwargs)


def _parse_album(data, artist=None):
    if artist is None:
        artist_name = "Unknown"
        if 'artist' in data:
            artist_name = data['artist']
        elif 'albumArtist' in data:
            artist_name = data['albumArtist']
        artist = Artist(name=artist_name)
        
    kwargs = {
        'id': data['albumId'],
        'name': data['name'],
        'artist': artist,
    }
    if 'albumArtRef' in data:
        kwargs['image'] = data['albumArtRef']
        
    if 'year' in data:
        kwargs['release_date'] = data['year']

    return Album(**kwargs)
