
from pytubefix import YouTube
 
url = "https://www.youtube.com/watch?v=MO7bRMa9bmA"
 
video = YouTube(url).streams.filter(progressive=True, file_extension="mp4").order_by('resolution').desc().first().download(output_path='./temp', filename="MyFileName.mp4")