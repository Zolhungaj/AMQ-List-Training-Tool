"""
This module downloads a lot of songs from anime music quiz
Dependencies:
ffmpeg
selenium
Firefox
geckodriver
"""
import os
import re
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import time
import json
from pathlib import Path
import subprocess
import sqlite3


class Database:

    def __init__(self, database_file):
        self.database_file = database_file
        conn = self.conn = sqlite3.connect(database_file)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS downloaded(
                source TEXT,
                annSongId INTEGER
            );""")
        conn.commit()
    
    def is_downloaded(self, song, source):
        c = self.conn.cursor()
        c.execute("""
        SELECT source
        FROM downloaded
        WHERE source=(?) AND annSongId = (?)
        """, (source, song["annSongId"],))
        return c.fetchone() is not None
    
    def add_downloaded(self, song, source):
        self.conn.execute("""
        INSERT INTO downloaded VALUES(?,?)
        """, (source, song["annSongId"]))
        self.conn.commit()


def update_anime_lists(driver, anilist="", kitsu=""):
    driver.execute_script('document.getElementById("mpNewsContainer").innerHTML = "Updating AniList...";')
    status = driver.find_element_by_id("mpNewsContainer")
    driver.execute_script("""new Listener("anime list update result", function (result) {
		if (result.success) {
			document.getElementById("mpNewsContainer").innerHTML = "Updated Successful: " + result.message;
		} else {
			document.getElementById("mpNewsContainer").innerHTML = "Update Unsuccessful: " + result.message;
		}
    }).bindListener()""")
    driver.execute_script("""
    socket.sendCommand({
		type: "library",
		command: "update anime list",
		data: {
			newUsername: arguments[0],
			listType: 'ANILIST'
		}
	});""", anilist)
    while True:
        if status.text != "Updating AniList...":
            break
        time.sleep(0.5)
    driver.execute_script('document.getElementById("mpNewsContainer").innerHTML = "Updating Kitsu...";')
    driver.execute_script("""
    socket.sendCommand({
		type: "library",
		command: "update anime list",
		data: {
			newUsername: arguments[0],
			listType: 'KITSU'
		}
	});""", kitsu)
    while True:
        if status.text != "Updating Kitsu...":
            break
        time.sleep(0.5)


def get_question_list(driver):
    driver.execute_script('document.getElementById("mpNewsContainer").innerHTML = "Loading Expand...";')
    script ="""new Listener("expandLibrary questions", function (payload) {
    expandLibrary.tackyVariable = (JSON.stringify(payload.questions));
    document.getElementById("mpNewsContainer").innerHTML = "Expand Loaded!"
}).bindListener();
socket.sendCommand({
    type: "library",
    command: "expandLibrary questions"
});"""
    driver.execute_script(script)
    status = driver.find_element_by_id("mpNewsContainer")
    while True:
        if status.text != "Loading Expand...":
            break
        time.sleep(0.5)
    time.sleep(3)
    pure_string = driver.execute_script('return expandLibrary.tackyVariable')
    driver.execute_script('expandLibrary.tackyVariable = ""')
    ret = json.loads(pure_string)
    driver.execute_script('document.getElementById("mpNewsContainer").innerHTML = "";')
    return ret

ffmpeg = "ffmpeg"


def main():
    """
    the main function, where the magic happens
    """
    with open("automator.config") as file:
        data = file.readlines()
        username = data[0][:-1]
        password = data[1][:-1]
        anilist = data[2][:-1]
        kitsu = data[3][:-1]
        global ffmpeg
        ffmpeg = data[4][:-1]
        outpath = data[5][:-1]
    path = Path(__file__).parent.absolute()
    if not outpath:
        outpath = path.joinpath(Path('out'))
    else:
        outpath = Path(outpath)
    print(str(path.joinpath(Path('geckodriver/geckodriver'))))
    driver = webdriver.Firefox(executable_path='geckodriver/geckodriver')
    driver.get('https://animemusicquiz.com')
    driver.find_element_by_id("loginUsername").send_keys(username)
    driver.find_element_by_id("loginPassword").send_keys(password)
    driver.find_element_by_id("loginButton").click()
    time.sleep(10)
    update_anime_lists(driver, anilist, kitsu)
    questions = get_question_list(driver)
    driver.execute_script("options.logout();")
    driver.close()
    database = Database("downloaded.db")
    for question in questions:
        annId = question["annId"]
        name = question["name"]
        songs = question["songs"]
        for song in songs:
            save(annId, name, song, outpath, database)


def save(annId, anime, song, outpath, database):
    source_mp3 = song["examples"].get("mp3", None)
    if not source_mp3:
        return
    if database.is_downloaded(song, source_mp3):
        return
    title = song["name"]
    artist = song["artist"]
    type = ["Unknown", "Opening", "Ending", "Insert"][song["type"]]
    number = song["number"]
    annSongId = song["annSongId"]
    command = [
        '"%s"' % ffmpeg, 
        "-y", 
        "-i", source_mp3,
        "-vn", 
        "-c:a", "copy",
        "-map_metadata", "-1",
        "-metadata", 'title="%s"' % title,
        "-metadata", 'artist="%s"' % artist,
        "-metadata", 'track="%d"' % number,
        "-metadata", 'disc="%d"' % song["type"],
        "-metadata", 'genre="%s"' % type,
        "-metadata", 'album="%s"' % anime,
        '"%s"' % create_file_name(anime, type, number, title, artist, annId, annSongId, outpath)
    ]
    execute_command(" ".join(command))
    database.add_downloaded(song, source_mp3)
    return True


def execute_command_Windows(command):
    print(command)
    print(type(command))
    os.system("start /wait /MIN cmd /c %s" % command)


def execute_command_POSIX(command):
    subprocess.call(command)


def create_file_name_Windows(animeTitle, songType, songNumber, songTitle, songArtist, annId, annSongId, path, allowance=255):
    """
    Creates a windows-compliant filename by removing all bad characters 
    and maintaining the windows path length limit (which by default is 255)
    """
    allowance -= len(str(path)) + 1 # by default, windows is sensitive to long total paths.
    bad_characters = re.compile(r"\\|/|<|>|:|\"|\||\?|\*|&|\^|\$|" + '\0')
    return create_file_name_common(animeTitle, songType, songNumber, songTitle, songArtist, annId, annSongId, path, bad_characters, allowance)


def create_file_name_POSIX(animeTitle, songType, songNumber, songTitle, songArtist, annId, annSongId, path, allowance=32767):
    """
    Creates a POSIX-compliant filename by removing all bad characters 
    and maintaining the NTFS path length limit
    """
    bad_characters = re.compile(r"/" + '\0')
    return create_file_name_common(animeTitle, songType, songNumber, songTitle, songArtist, annId, annSongId, path, bad_characters, allowance)


def create_file_name_common(animeTitle, songType, songNumber, songTitle, songArtist, annId, annSongId, path, bad_characters, allowance=255):
    if allowance > 255: 
        allowance = 255 # on most common filesystems, including NTFS a filename can not exceed 255 characters
    # assign allowance for things that must be in the file name
    allowance -= len(str(annId))
    allowance -= len(str(annSongId))
    allowance -= len("_-.mp3") # accounting for separators (-_) for annId annSongId, and .mp3
    if allowance < 0:
        raise ValueError("""It is not possible to give a reasonable file name, due to length limitations.
        Consider changing location to somewhere with a shorter path.""")
    # make sure that user input doesn't contain bad characters
    animeTitle = bad_characters.sub("", animeTitle)
    songType = bad_characters.sub('', songType)
    songTitle = bad_characters.sub('', songTitle)
    songArtist = bad_characters.sub('', songArtist)

    song_number_string = ""
    if songNumber:
        song_number_string = "_" + str(songNumber)
    ret = ""
    for string in [animeTitle, songType + song_number_string, songTitle, songArtist]:
        length = len(string)
        if allowance - length < 0:
            string = string[:allowance]
            length = len(string)
        ret += string
        allowance -= length
        if allowance - 1 > 1:
            ret += "-"
        else:
            break
    else:
        ret = ret[:-1] # removes last "-"
    ret = path.joinpath(Path(ret + "_" + str(annId) + "-" + str(annSongId) + ".mp3"))

    return str(ret)


if os.name == "nt":
    create_file_name = create_file_name_Windows
    execute_command = execute_command_Windows
elif os.name == "posix":
    create_file_name = create_file_name_POSIX
    execute_command = execute_command_POSIX


if __name__ == "__main__":
    main()
