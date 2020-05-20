# Fractal test is from: https://www.youtube.com/watch?v=WgXQ59rg0GM

from pathlib import Path

test_video = str(Path.joinpath(Path(__file__).parent, "fractal test.mp4"))
test_video_2 = str(Path.joinpath(Path(__file__).parent, "fractal test 2.mp4"))
test_video_3 = str(Path.joinpath(Path(__file__).parent, "fractal test 3.mp4"))

urls = {
    "test_video": "https://www.youtube.com/watch?v=LpWhaBVIrZw",
    "test_video_2": "https://www.youtube.com/watch?v=GASynpGr-c8",
    "test_video_3": "https://www.youtube.com/watch?v=u_P83LcI8Oc"
}


def populate_videos(fps=60, res="720p", ext="mp4"):
    from pytube import YouTube  # Note: pip install pytube3, not pytube
    from pathlib import Path
    for n, v in globals().items():
        if 'test_video' in n:
            print(f"Checking if '{n}' is downloaded.")
            if Path(v).exists():
                print("Video already downloaded.")
            else:
                the_path = Path(v)
                print("Downloading...")
                YouTube(urls[n]) \
                    .streams \
                    .filter(fps=fps, res=res, file_extension=ext)[0] \
                    .download(output_path=the_path.parent, filename=the_path.stem)


if __name__ == "__main__":
    populate_videos()
