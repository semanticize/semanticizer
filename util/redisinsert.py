import sys
from wpm.wpmdata_redis import WpmLoader

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print "Usage: %s language_name language_code path_to_wpm_dump" \
               % sys.argv[0]
        sys.exit(1)
    try:
        loader = WpmLoader()
        loader.load_wpminer_dump(sys.argv[1], sys.argv[2], sys.argv[3])
    except IOError as err:
        print err.message
