import sys
import os
import time
import re
# Shared resources
BASE_RESOURCE_PATH = os.path.join( os.getcwd(), "resources" )
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )
cacheDir = os.path.join( os.getcwd(), "cache/" )
import random,xbmcplugin,xbmcgui,python_SHA256, datetime, time, urllib,urllib2, elementtree.ElementTree as ET

try:
    # new XBMC 10.05 addons:
    import xbmcaddon
except ImportError:
    # old XBMC - create fake xbmcaddon module with same interface as new XBMC 10.05
    class xbmcaddon:
        """ fake xbmcaddon module """
        __version__ = "(old XBMC)"
        class Addon:
            """ fake xbmcaddon.Addon class """
            def __init__(self, id):
                self.id = id
            def getSetting(self, key):
                return xbmcplugin.getSetting(key)
            def setSetting(self, key, value):
                xbmcplugin.setSetting(key, value)
            def openSettings(self, key, value):
                xbmc.openSettings()
            def getLocalizedString(self, id):
                return xbmc.getLocalizedString(id)

ampache = xbmcaddon.Addon("plugin.audio.ampache")
imagepath = os.path.join(os.getcwd().replace(';', ''),'resources','images')

def cacheArt(url):
	strippedAuth = url.split('&')
	imageID = re.search(r"id=(\d+)", strippedAuth[0])

	if os.path.exists(cacheDir + imageID.group(1) + ".png"):
		print "DEBUG: png cached"
		return cacheDir + imageID.group(1) + ".png"
	elif os.path.exists(cacheDir + imageID.group(1) + ".jpg"):
		print "DEBUG: jpg cached"
		return cacheDir + imageID.group(1) + ".jpg"
	else:
		print "DEBUG: File needs fetching"
		opener = urllib.urlopen(url)
		if opener.headers.maintype == 'image':
			extension = opener.headers['content-type']
			tmpExt = extension.split("/")
			if tmpExt[1] == "jpeg":
				fname = imageID.group(1) + '.jpg'
			else:
				fname = imageID.group(1) + '.' + tmpExt[1]
			open( cacheDir + fname, 'wb').write(opener.read())
			print "DEBUG: Cached " + fname
			return fname
		else:
			print "DEBUG: It didnt work"
			return False

def enableAlarm():
    alarm_hour = int(ampache.getSetting('alarm_hour'))
    alarm_minute = int(ampache.getSetting('alarm_minute'))
    current_hour = time.localtime().tm_hour
    current_minute = time.localtime().tm_min
    if (current_hour < alarm_hour) or ((current_hour == alarm_hour) and (current_minute < alarm_minute)):
        wait_mins = ((alarm_hour - current_hour) * 60) - current_minute + alarm_minute
    elif (current_hour > alarm_hour) or ((current_hour == alarm_hour) and (current_minute > alarm_minute)):
        wait_mins = ((23 - current_hour) * 60) + (60 - current_minute) + (alarm_hour * 60) + alarm_minute
    execCMD = 'PlayMedia(plugin://plugin.audio.ampache/?mode=9)'
    builtinCMD = 'XBMC.AlarmClock(%s,%s,%s)' % ('myAlarm', execCMD, wait_mins)
    xbmc.executebuiltin(builtinCMD.encode('latin-1'))

def cancelAlarm():
    builtinCMD = 'XBMC.CancelAlarm(myAlarm)'
    xbmc.executebuiltin(builtinCMD.encode('latin-1'))

# called from a context menu on a song object
def setAlarm(object_id):
    ampache.setSetting(id='alarm_song', value=str(object_id) )
    
def addLink(name,url,iconimage,node):
        ok=True
        liz=xbmcgui.ListItem(name, iconImage=iconimage, thumbnailImage=iconimage)
        liz.setInfo( type="Music", infoLabels={ "Title": node.findtext("title"), "Artist": node.findtext("artist"), "Album": node.findtext("album"), "TrackNumber": str(node.findtext("track")) } )
        ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=url,listitem=liz)
        return ok

# Used to populate items for songs on XBMC. Calls plugin script with mode == 8 and object_id == (ampache song id)
# TODO: Merge with addDir(). Same basic idea going on, this one adds links all at once, that one does it one at a time
#       Also, some property things, some different context menu things.
def addLinks(elem):
	xbmcplugin.setContent(int(sys.argv[1]), "songs")
	ok=True
	li=[]
	for node in elem:
		cm = []
		albumArt = cacheArt(node.findtext("art"))
		print "DEBUG: albumArt - " + albumArt
		liz=xbmcgui.ListItem(label=node.findtext("title").encode("utf-8"), thumbnailImage=albumArt)
		# liz=xbmcgui.ListItem(label=node.findtext("title").encode("utf-8"), thumbnailImage=node.findtext("art"))


		liz.setInfo( "music", { "title": node.findtext("title").encode("utf-8"), "artist": node.findtext("artist"), "album": node.findtext("album"), "ReleaseDate": str(node.findtext("year")) } )
		liz.setProperty("mimetype", 'audio/mpeg')
		liz.setProperty("IsPlayable", "true")
		song_elem = node.find("song")
		song_id = int(node.attrib["id"])
		action = 'XBMC.RunPlugin(%s?object_id=%s&mode=10)' % ( sys.argv[0],song_id )
		cm.append( ( "Set as Alarm", action  ) )
		liz.addContextMenuItems(cm)
		track_parameters = { "mode": 8, "object_id": song_id}
		url = sys.argv[0] + '?' + urllib.urlencode(track_parameters)
		tu= (url,liz)
		li.append(tu)
	ok=xbmcplugin.addDirectoryItems(handle=int(sys.argv[1]),items=li,totalItems=len(elem))
	return ok

# The function that actually plays an Ampache URL by using setResolvedUrl. Gotta have the extra step in order to make
# song album art / play next automatically. We already have the track URL when we add the directory item so the api
# hit here is really unnecessary. Would be nice to get rid of it, the extra request adds to song gaps. It does
# guarantee that we are using a legit URL, though, if the session expired between the item being added and the actual
# playing of that item.
def play_track(id):
    ''' Start to stream the track with the given id. '''
    elem = ampache_http_request("song",filter=id)
    for thisnode in elem:
        node = thisnode
    albumArt = cacheArt(node.findtext("art"))
    # li = xbmcgui.ListItem(label=node.findtext("title").encode("utf-8"), thumbnailImage=node.findtext("art"), path=node.findtext("url"))
    li = xbmcgui.ListItem(label=node.findtext("title").encode("utf-8"), thumbnailImage=albumArt, path=node.findtext("url"))
    li.setInfo("music", { "title": node.findtext("title") })
    xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=True, listitem=li)

# Wrapper around play_track to make sure that we have a valid Ampache session.
# TODO: We shouldn't force a new session if we already have one.
def play_alarm():
    AMPACHECONNECT()
    play_track(ampache.getSetting('alarm_song'))

# Main function for adding xbmc plugin elements
def addDir(name,object_id,mode,iconimage,elem=None,artFilename=None):
	if artFilename:
#		liz=xbmcgui.ListItem(name, iconImage=artFilename, thumbnailImage=iconimage)
		liz=xbmcgui.ListItem(name, iconImage=artFilename, thumbnailImage=artFilename)
	else:
		liz=xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)

	liz.setInfo( type="Music", infoLabels={ "Title": name } )
	try:
		artist_elem = elem.find("artist")
		artist_id = int(artist_elem.attrib["id"]) 
		cm = []
		cm.append( ( "Show all albums from artist", "XBMC.Container.Update(%s?object_id=%s&mode=2)" % ( sys.argv[0],artist_id ) ) )
		liz.addContextMenuItems(cm)
	except:
		pass
	u=sys.argv[0]+"?object_id="+str(object_id)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)
	ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
	return ok

def get_params():
    param=[]
    paramstring=sys.argv[2]
    if len(paramstring)>=2:
            params=sys.argv[2]
            cleanedparams=params.replace('?','')
            if (params[len(params)-1]=='/'):
                    params=params[0:len(params)-2]
            pairsofparams=cleanedparams.split('&')
            param={}
            for i in range(len(pairsofparams)):
                    splitparams={}
                    splitparams=pairsofparams[i].split('=')
                    if (len(splitparams))==2:
                            param[splitparams[0]]=splitparams[1]
                            
    return param
    
def getFilterFromUser():
    loop = True
    while(loop):
        kb = xbmc.Keyboard('', '', True)
        kb.setHeading('Enter Search Filter')
        kb.setHiddenInput(False)
        kb.doModal()
        if (kb.isConfirmed()):
            filter = kb.getText()
            loop = False
        else:
            return(False)
    return(filter)

def AMPACHECONNECT():
    nTime = int(time.time())
    myTimeStamp = str(nTime)
    sdf = ampache.getSetting("password")
    hasher = python_SHA256.new()
    hasher.update(ampache.getSetting("password"))
    myKey = hasher.hexdigest()
    hasher = python_SHA256.new()
    hasher.update(myTimeStamp + myKey)
    myPassphrase = hasher.hexdigest()
    myURL = ampache.getSetting("server") + 'server/xml.server.php?action=handshake&auth='
    myURL += myPassphrase + "&timestamp=" + myTimeStamp
    myURL += '&version=350001&user=' + ampache.getSetting("username")
    xbmc.log(myURL,xbmc.LOGNOTICE)
    req = urllib2.Request(myURL)
    response = urllib2.urlopen(req)
    tree=ET.parse(response)
    response.close()
    elem = tree.getroot()
    token = elem.findtext('auth')
    ampache.setSetting('token',token)
    ampache.setSetting('token-exp',str(nTime+24000))
    return elem

def ampache_http_request(action,add=None, filter=None, limit=5000, offset=0):
    thisURL = build_ampache_url(action,filter=filter,add=add,limit=limit,offset=offset)
    req = urllib2.Request(thisURL)
    response = urllib2.urlopen(req)
    tree=ET.parse(response)
    response.close()
    elem = tree.getroot()
    if elem.findtext("error"):
        errornode = elem.find("error")
        if errornode.attrib["code"]=="401":
            elem = AMPACHECONNECT()
            thisURL = build_ampache_url(action,filter=filter,add=add,limit=limit,offset=offset)
            req = urllib2.Request(thisURL)
            response = urllib2.urlopen(req)
            tree=ET.parse(response)
            response.close()
            elem = tree.getroot()
    return elem
    
def get_items(object_type, artist=None, add=None, filter=None, playlist=None, playlist_song=None):
    xbmcplugin.setContent(int(sys.argv[1]), object_type)
    action = object_type
    if artist:
        filter = artist
        action = 'artist_albums'
    elif playlist:
        action = 'playlist'
        filter = playlist
    elif playlist_song:
        action = 'playlist_song'
        filter = playlist_song
    elem = ampache_http_request(action,add=add,filter=filter)
    if object_type == 'artists':
        mode = 2
        image = "DefaultFolder.png"
    elif object_type == 'albums':
        mode = 3
    elif object_type == 'playlists':
        mode = 14
    	image = "DefaultFolder.png"
    elif object_type == 'playlist_song':
        mode = 15
        image = "DefaultFolder.png"
    for node in elem:
        if object_type == 'albums':
            print "DEBUG: object_type - " + str(object_type)
            print "DEBUG: Art - " + str(node.findtext("art"))
            artFilename = cacheArt(node.findtext("art"))
            print "DEBUG: Art Filename: " + artFilename
            image = node.findtext("art")
        try:
        	artFilename
        except NameError:
        	addDir(node.findtext("name").encode("utf-8"),node.attrib["id"],mode,image,node)
        else:
        	addDir(node.findtext("name").encode("utf-8"),node.attrib["id"],mode,image,node, artFilename = artFilename)

def GETSONGS(objectid=None,filter=None,add=None,limit=5000,offset=0,playlist=None):
    xbmcplugin.setContent(int(sys.argv[1]), 'songs')
    if filter:
        action == 'songs'
    elif playlist:
        action = 'playlist_songs'
        filter = playlist
    elif objectid:
        action = 'album_songs'
        filter = objectid
    else:
        action = 'songs'
    elem = ampache_http_request(action,add=add,filter=filter)
    addLinks(elem)

def build_ampache_url(action,filter=None,add=None,limit=5000,offset=0):
    tokenexp = int(ampache.getSetting('token-exp'))
    if int(time.time()) > tokenexp:
        print "refreshing token..."
        elem = AMPACHECONNECT()

    token=ampache.getSetting('token')    
    thisURL = ampache.getSetting("server") + 'server/xml.server.php?action=' + action 
    thisURL += '&auth=' + token
    thisURL += '&limit=' +str(limit)
    thisURL += '&offset=' +str(offset)
    if filter:
        thisURL += '&filter=' +urllib.quote_plus(str(filter))
    if add:
        thisURL += '&add=' + add
    return thisURL

def get_random_albums():
    xbmcplugin.setContent(int(sys.argv[1]), 'albums')
    elem = AMPACHECONNECT()
    albums = int(elem.findtext('albums'))
    print albums
    random_albums = (int(ampache.getSetting("random_albums"))*3)+3
    print random_albums
    seq = random.sample(xrange(albums),random_albums)
    for album_id in seq:
        elem = ampache_http_request('albums',offset=album_id,limit=1)
        for node in elem:
	    fullname = node.findtext("name").encode("utf-8")
	    fullname += " - "
	    fullname += node.findtext("artist").encode("utf-8")
	addDir(fullname,node.attrib["id"],3,node.findtext("art"),node)        


params=get_params()
name=None
mode=None
object_id=None

try:
        name=urllib.unquote_plus(params["name"])
except:
        pass
try:
        mode=int(params["mode"])
except:
        pass
try:
        object_id=int(params["object_id"])
except:
        pass

print "Mode: "+str(mode)
print "Name: "+str(name)
print "ObjectID: "+str(object_id)

if mode==None:
    print ""
    elem = AMPACHECONNECT()
    addDir("Search...",0,4,"DefaultFolder.png")
    addDir("Recent...",0,5,"DefaultFolder.png")
    addDir("Random...",0,7,"DefaultFolder.png")
    addDir("Artists (" + str(elem.findtext("artists")) + ")",None,1,"DefaultFolder.png")
    addDir("Albums (" + str(elem.findtext("albums")) + ")",None,2,"DefaultFolder.png")
    addDir("Playlists (" + str(elem.findtext("playlists")) + ")",None,13,"DefaultFolder.png")
    liz=xbmcgui.ListItem('Set Alarm')
    url=sys.argv[0]+"?mode=11"
    ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=url,listitem=liz)
    liz=xbmcgui.ListItem('Cancel Alarm')
    url=sys.argv[0]+"?mode=12"
    ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=url,listitem=liz)

elif mode==1:
    if object_id == 99999:
        thisFilter = getFilterFromUser()
        if thisFilter:
            get_items(object_type="artists",filter=thisFilter)
    elif object_id == 99998:
        elem = AMPACHECONNECT()
        update = elem.findtext("add")        
        xbmc.log(update[:10],xbmc.LOGNOTICE)
        get_items(object_type="artists",add=update[:10])
    elif object_id == 99997:
        d = datetime.date.today()
        dt = datetime.timedelta(days=-7)
        nd = d + dt
        get_items(object_type="artists",add=nd.isoformat())
    elif object_id == 99996:
        d = datetime.date.today()
        dt = datetime.timedelta(days=-30)
        nd = d + dt
        get_items(object_type="artists",add=nd.isoformat())
    elif object_id == 99995:
        d = datetime.date.today()
        dt = datetime.timedelta(days=-90)
        nd = d + dt
        get_items(object_type="artists",add=nd.isoformat())
    else:
        get_items(object_type="artists")
       
elif mode==2:
        print ""
        if object_id == 99999:
            thisFilter = getFilterFromUser()
            if thisFilter:
                get_items(object_type="albums",filter=thisFilter)
        elif object_id == 99998:
            elem = AMPACHECONNECT()
            update = elem.findtext("add")        
            xbmc.log(update[:10],xbmc.LOGNOTICE)
            get_items(object_type="albums",add=update[:10])
        elif object_id == 99997:
            d = datetime.date.today()
            dt = datetime.timedelta(days=-7)
            nd = d + dt
            get_items(object_type="albums",add=nd.isoformat())
        elif object_id == 99996:
            d = datetime.date.today()
            dt = datetime.timedelta(days=-30)
            nd = d + dt
            get_items(object_type="albums",add=nd.isoformat())
        elif object_id == 99995:
            d = datetime.date.today()
            dt = datetime.timedelta(days=-90)
            nd = d + dt
            get_items(object_type="albums",add=nd.isoformat())
        elif object_id:
            get_items(object_type="albums",artist=object_id)
        else:
            get_items(object_type="albums")
        
elif mode==3:
        print ""
        if object_id == 99999:
            thisFilter = getFilterFromUser()
            if thisFilter:
                GETSONGS(filter=thisFilter)
        elif object_id == 99998:
            elem = AMPACHECONNECT()
            update = elem.findtext("add")        
            xbmc.log(update[:10],xbmc.LOGNOTICE)
            GETSONGS(add=update[:10])
        elif object_id == 99997:
            d = datetime.date.today()
            dt = datetime.timedelta(days=-7)
            nd = d + dt
            GETSONGS(add=nd.isoformat())
        elif object_id == 99996:
            d = datetime.date.today()
            dt = datetime.timedelta(days=-30)
            nd = d + dt
            GETSONGS(add=nd.isoformat())
        elif object_id == 99995:
            d = datetime.date.today()
            dt = datetime.timedelta(days=-90)
            nd = d + dt
            GETSONGS(add=nd.isoformat())
        else:
            GETSONGS(objectid=object_id)

elif mode==4:
    addDir("Search Artists...",99999,1,"DefaultFolder.png")
    addDir("Search Albums...",99999,2,"DefaultFolder.png")
    addDir("Search Songs...",99999,3,"DefaultFolder.png")

elif mode==5:
    addDir("Recent Artists...",99998,6,"DefaultFolder.png")
    addDir("Recent Albums...",99997,6,"DefaultFolder.png")
    addDir("Recent Songs...",99996,6,"DefaultFolder.png")

elif mode==6:
    addDir("Last Update",99998,99999-object_id,"DefaultFolder.png")
    addDir("1 Week",99997,99999-object_id,"DefaultFolder.png")
    addDir("1 Month",99996,99999-object_id,"DefaultFolder.png")
    addDir("3 Months",99995,99999-object_id,"DefaultFolder.png")

elif mode==7:
    addDir("Refresh...",0,7,os.path.join(imagepath, 'refresh_icon.png'))
    get_random_albums()

elif mode==8:
    play_track(object_id)

elif mode==9:
    play_alarm()

elif mode==10:
    setAlarm(object_id)

elif mode==11:
    enableAlarm()

elif mode==12:
    cancelAlarm()

elif mode==13:
#    print "Hello Ampache!!"
#    get_items(object_type="playlists")
        print "Hello Ampache!!!"
        if object_id == 99999:
            thisFilter = getFilterFromUser()
            if thisFilter:
                get_items(object_type="playlists",filter=thisFilter)
        elif object_id == 99998:
            elem = AMPACHECONNECT()
            update = elem.findtext("add")        
            xbmc.log(update[:10],xbmc.LOGNOTICE)
            get_items(object_type="playlists",add=update[:10])
        elif object_id == 99997:
            d = datetime.date.today()
            dt = datetime.timedelta(days=-7)
            nd = d + dt
            get_items(object_type="playlists",add=nd.isoformat())
        elif object_id == 99996:
            d = datetime.date.today()
            dt = datetime.timedelta(days=-30)
            nd = d + dt
            get_items(object_type="playlists",add=nd.isoformat())
        elif object_id == 99995:
            d = datetime.date.today()
            dt = datetime.timedelta(days=-90)
            nd = d + dt
            get_items(object_type="playlists",add=nd.isoformat())
        elif object_id:
            get_items(object_type="playlists",artist=object_id)
        else:
            get_items(object_type="playlists")

elif mode==14:
#    print "Hello Ampache!!"
#    get_items(object_type="playlists")
        print "Hello Ampache Playlists!!!"
        if object_id == 99999:
            thisFilter = getFilterFromUser()
            if thisFilter:
                get_items(object_type="playlist_song",filter=thisFilter)
        elif object_id == 99998:
            elem = AMPACHECONNECT()
            update = elem.findtext("add")        
            xbmc.log(update[:10],xbmc.LOGNOTICE)
            get_items(object_type="playlist_song",add=update[:10])
        elif object_id == 99997:
            d = datetime.date.today()
            dt = datetime.timedelta(days=-7)
            nd = d + dt
            get_items(object_type="playlist_song",add=nd.isoformat())
        elif object_id == 99996:
            d = datetime.date.today()
            dt = datetime.timedelta(days=-30)
            nd = d + dt
            get_items(object_type="playlist_song",add=nd.isoformat())
        elif object_id == 99995:
            d = datetime.date.today()
            dt = datetime.timedelta(days=-90)
            nd = d + dt
            get_items(object_type="playlist_song",add=nd.isoformat())
        elif object_id:
            get_items(object_type="playlist_song",playlist=object_id)
        else:
            get_items(object_type="playlist_song")

elif mode==15:
    print "Hello Ampache Playlist1!!!"
    GETSONGS(playlist=object_id)
    
if mode < 19:
    xbmcplugin.endOfDirectory(int(sys.argv[1]))
