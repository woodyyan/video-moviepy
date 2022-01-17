import os
import subprocess as sp

from .compat import DEVNULL
from .config_defaults import FFMPEG_BINARY, IMAGEMAGICK_BINARY

if os.name == 'nt':
    try:
        import winreg as wr  # py3k
    except ImportError:
        import _winreg as wr  # py2k


def try_cmd(cmd):
    try:
        popen_params = {
            "stdout": sp.PIPE,
            "stderr": sp.PIPE,
            "stdin": DEVNULL
        }

        # This was added so that no extra unwanted window opens on windows
        # when the child process is created
        if os.name == "nt":
            popen_params["creationflags"] = 0x08000000

        proc = sp.Popen(cmd, **popen_params)
        proc.communicate()
    except Exception as err:
        return False, err
    else:
        return True, None


if FFMPEG_BINARY == 'ffmpeg-imageio':
    from imageio.plugins.ffmpeg import get_exe

    FFMPEG_BINARY = get_exe()

elif FFMPEG_BINARY == 'auto-detect':

    if try_cmd(['ffmpeg'])[0]:
        FFMPEG_BINARY = 'ffmpeg'
    elif try_cmd(['ffmpeg.exe'])[0]:
        FFMPEG_BINARY = 'ffmpeg.exe'
    else:
        FFMPEG_BINARY = 'unset'
else:
    success, err = try_cmd([FFMPEG_BINARY])
    if not success:
        raise IOError(
            str(err) +
            " - The path specified for the ffmpeg binary might be wrong")

if IMAGEMAGICK_BINARY == 'auto-detect':
    if os.name == 'nt':
        try:
            key = wr.OpenKey(wr.HKEY_LOCAL_MACHINE, 'SOFTWARE\\ImageMagick\\Current')
            IMAGEMAGICK_BINARY = wr.QueryValueEx(key, 'BinPath')[0] + r"\convert.exe"
            key.Close()
        except:
            IMAGEMAGICK_BINARY = 'unset'
    elif try_cmd(['convert'])[0]:
        IMAGEMAGICK_BINARY = 'convert'
    else:
        IMAGEMAGICK_BINARY = 'unset'
else:
    if not os.path.exists(IMAGEMAGICK_BINARY):
        raise IOError(
            "ImageMagick binary cannot be found at {}".format(
                IMAGEMAGICK_BINARY
            )
        )

    if not os.path.isfile(IMAGEMAGICK_BINARY):
        raise IOError(
            "ImageMagick binary found at {} is not a file".format(
                IMAGEMAGICK_BINARY
            )
        )

    success, err = try_cmd([IMAGEMAGICK_BINARY])
    if not success:
        raise IOError("%s - The path specified for the ImageMagick binary might "
                      "be wrong: %s" % (err, IMAGEMAGICK_BINARY))


def get_setting(varname):
    """ Returns the value of a configuration variable. """
    gl = globals()
    if varname not in gl.keys():
        raise ValueError("Unknown setting %s" % varname)
    # Here, possibly add some code to raise exceptions if some
    # parameter isn't set set properly, explaining on how to set it.
    return gl[varname]


def change_settings(new_settings=None, filename=None):
    """ Changes the value of configuration variables."""
    new_settings = new_settings or {}
    gl = globals()
    if filename:
        with open(filename) as in_file:
            exec(in_file)
        gl.update(locals())
    gl.update(new_settings)
    # Here you can add some code  to check that the new configuration
    # values are valid.


if __name__ == "__main__":
    if try_cmd([FFMPEG_BINARY])[0]:
        print("MoviePy : ffmpeg successfully found.")
    else:
        print("MoviePy : can't find or access ffmpeg.")

    if try_cmd([IMAGEMAGICK_BINARY])[0]:
        print("MoviePy : ImageMagick successfully found.")
    else:
        print("MoviePy : can't find or access ImageMagick.")
