"""
Scripts sub-module of HiPERCAM contains all the commands used from
the terminal. They are all implemented as functions for automatic
inclusion in the documentation and for portability
"""

from .aligntool import aligntool
from .arith import add, div, mul, sub
from .averun import averun
from .carith import cadd, cdiv, cmul, csub
from .combine import combine
from .grab import grab
from .genred import genred
from .hist import hist
from .hlogger import hlogger
from .hls import hls
from .hplot import hplot
from .makebias import makebias
from .makeflat import makeflat
from .makestuff import makedata, makefield
from .plog import plog
from .reduce import reduce
from .rtplot import rtplot
from .setaper import setaper
from .stats import stats
from .times import times

# important to keep alphabetical ordering here for sphinx / autodoc

__all__ = [ \
            'add', 'aligntool', 'averun',
            'cadd', 'cdiv', 'cmul', 'combine', 'csub',
            'div',
            'genred', 'grab',
            'hist', 'hlogger', 'hls', 'hplot',
            'makebias', 'makedata', 'makefield', 'makeflat', 'mul',
            'plog',
            'reduce', 'rtplot',
            'setaper', 'stats', 'sub',
            'times',
        ]
