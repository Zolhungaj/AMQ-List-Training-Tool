"""
This module downloads a lot of songs from anime music quiz
Dependencies:
ffmpeg
selenium
Firefox
geckodriver
"""
import os
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import time
import json
from pathlib import Path

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

ffmpeg = "ffmpeg"  # command to invoke ffmpeg, eg C:ffmpeg\bin\ffmpeg.exe


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
    path = str(Path(__file__).parent.absolute())
    if not outpath:
        outpath = path+"/out/"
    driver = webdriver.Firefox(executable_path=path+'/geckodriver/geckodriver')
    driver.get('https://animemusicquiz.com')
    driver.find_element_by_id("loginUsername").send_keys(username)
    driver.find_element_by_id("loginPassword").send_keys(password)
    driver.find_element_by_id("loginButton").click()
    time.sleep(10)
    update_anime_lists(driver, anilist, kitsu)
    questions = get_question_list(driver)
    driver.execute_script("options.logout();")
    driver.close()
    for question in questions:
        annId = question["annId"]
        name = question["name"]
        songs = question["songs"]
        for song in songs:
            save(annId, name, song, outpath)


def save(annId, anime, song, outpath):
    source_mp3 = song["examples"].get("mp3", None)
    if not source_mp3:
        return
    title = song["name"]
    artist = song["artist"]
    type = ["Unknown", "Opening", "Ending", "Insert"][song["type"]]
    number = song["number"]
    annSongId = song["annSongId"]
    command = ffmpeg + " "
    command += "-y -i " + source_mp3 + " "
    command += "-vn -c:a copy" + " "
    command += "-map_metadata -1" + " "
    command += '-metadata title="%s" ' % title
    command += '-metadata artist="%s" ' % artist
    command += '-metadata track="%d" ' % number
    command += '-metadata disc="%d" ' % song["type"]
    command += '-metadata genre="%s" ' % type
    command += '-metadata album="%s" ' % anime
    command += '"out/' + anime + "-" + type + str(number) + "-" + title + "-" + artist + "_" + str(annId) + "-" + str(annSongId) + '.mp3"'
    execute_command(command)


def execute_command(command):
    os.system("start /wait /MIN cmd /c %s" % command)


def create_file_name_Windows(animeTitle, songType, songNumber, songTitle, songArtist, annId, annSongId, path, allowance=255):
    """
    Creates a windows-compliant filename by removing all bad characters 
    and maintaining the windows path length limit (which by default is 255)
    """
    allowance -= len(path) # by default, windows is sensitive to long total paths.
    bad_characters = re.compile(r"\\|/|<|>|:|\"|\||\?|\*|&|\^|\$|" + '\0')
    return create_file_name(animeTitle, songType, songNumber, songTitle, songArtist, annId, annSongId, path, bad_characters, allowance)


def create_file_name_POSIX(animeTitle, songType, songNumber, songTitle, songArtist, annId, annSongId, path, allowance=32767):
    """
    Creates a POSIX-compliant filename by removing all bad characters 
    and maintaining the NTFS path length limit
    """
    bad_characters = re.compile(r"/" + '\0')
    return create_file_name(animeTitle, songType, songNumber, songTitle, songArtist, annId, annSongId, path, bad_characters, allowance)


def create_file_name(animeTitle, songType, songNumber, songTitle, songArtist, annId, annSongId, path, bad_characters, allowance=255)
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
    ret = path + ret + "_" + str(annId) + "-" + str(annSongId) + ".mp3"

    return ret


if __name__ == "__main__":
    main()
