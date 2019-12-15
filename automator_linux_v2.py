"""
This module downloads a lot of songs from anime music quiz
Dependencies:
ffmpeg
selenium
Firefox
geckodriver
"""
import os
import subprocess
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import time
import json

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
    for question in questions:
        annId = question["annId"]
        name = question["name"]
        songs = question["songs"]
        for song in songs:
            save(driver, annId, name, song)


def save(driver, annId, anime, song):
    source_mp3 = song["examples"].get("mp3", None)
    if(not source_mp3):
        return
    title = song["name"]
    artist = song["artist"]
    song_type = ["Unknown", "Opening", "Ending", "Insert"][song["type"]]
    number = "" if song_type == "Insert" else str(song["number"])
    command = ["ffmpeg", "-y", "-i", source_mp3, "-vn", "-c:a", "copy",
            "-map_metadata", "-1",
            "-metadata", u"title={}".format(title),
            "-metadata", u"artist={}".format(artist),
            "-metadata", u"track={}".format(number),
            "-metadata", u"disc={}".format(song["type"]),
            "-metadata", u"genre={}".format(song_type),
            "-metadata", u"album={}".format(anime),
            u"out/{}-{}{}-{}-{}_{}-{}.mp3".format(
                anime, song_type, number, title, artist, annId, song["annSongId"])]
    subprocess.call(command)

if __name__ == "__main__":
    main()
