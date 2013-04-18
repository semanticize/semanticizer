import pstats
import sys

if __name__ == '__main__':
    stats = pstats.Stats(sys.argv[1])
    stats.sort_stats('time')
    stats.print_stats(.01)
    stats.print_callers(.01)
