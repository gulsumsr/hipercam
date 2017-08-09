"""
Section for handling the raw HiPERCAM data files. These are FITS files
with a single HDU containing extensive header information and the data in
a "FITS cube" of unusual nature.
"""

import struct
import warnings
import numpy as np
import urllib.request

from numpy.lib.stride_tricks import as_strided
import fitsio
from astropy.io import fits

from hipercam import (CCD, Group, MCCD, Windat, Window, HCM_NXTOT, HCM_NYTOT)

from .herrors import *

__all__ = ['Rhead', 'Rdata']

class Rhead:
    """Reads an interprets header information from a HiPERCAM run and
    generates the window formats needed to interpret the data. The file is
    kept open while the Rhead exists.

    The following attributes are set::

      cheads  : (list of astropy.io.fits.Header)
         the headers for each CCD which contain any info needed per CCD, above
         all the 'skip' numbers.

      ffile   : (fitsio.FITS)
         the opened file

      fname   : (string)
         the file name

      header  : (fitsio??)
         the header of the FITS file

      thead   : (astropy.io.fits.Header)
         the top-level header

      windows : (list of Windows)
         the windows are the same for each CCD, so these are just one set
         in EFGH order for window 1 and then the same for window 2 if there
         is one, so either 4 or 8 Windows.

    """

    def __init__(self, fname, server=False, full=True):
        """Opens a fits file containing HiPERCAM data, reads and interprets
        the header of the primary HDU.

        Arguments::

           fname  : (string)
              file name

           server : (bool)
              True to access the data from a server. It uses a URL set in an
              environment variable "HIPERCAM_DEFAULT_URL" in this instance.

           full   : (bool)
              Flag controlling the amount of header detail to gather (as a
              time saver) True for detail, False for the bare minimum, the
              latter might be useful for large numbers of very small format
              images where you don't to waste effort.
        """

        # store the file name
        self.fname = fname

        # open the file with fitsio
        self.ffile = fitsio.FITS(fname)

        # read the header
        self.header = self.ffile[0].read_header()

        # create the top-level header
        self.thead = fits.Header()

        # set the mode, one or two windows per quadrant, drift etc.
        # This is essential.
        mode = self.header['ESO DET READ CURNAME']
        self.thead['MODE'] = (mode,'HiPERCAM readout mode')

        # fixed data for each quadrant in tuples
        LLX = (1, 1025, 1025, 1)
        LLY = (1, 1, 521, 521)
        READOUT_Y = (1, 1, 1040, 1040)
        OFFSET = (1, 1, -1, -1)
        ADD_YSIZE = (0, 0, 1, 1)
        QUAD = ('E', 'F', 'G', 'H')

        # extract the binning factors
        xbin = self.header['ESO DET BINX1']
        ybin = self.header['ESO DET BINY1']

        # extract the data needed to build the Windows, according to the mode
        if mode.startswith('FullFrame'):
            nx = 1024 // xbin
            ny = 520 // ybin
            llxs = LLX
            llys = LLY

        elif mode.startswith('OneWindow'):
            nx = self.header['ESO DET WIN1 NX'] // xbin
            ny = self.header['ESO DET WIN1 NY'] // ybin
            llxs = [llx + self.header['ESO DET WIN1 XS{}'.format(quad)]
                    for llx, quad in zip(LLX, QUAD)]
            llys = [
                readout_y + offset*self.header['ESO DET WIN1 YS'] -
                add_ysize*self.header['ESO DET WIN1 NY']
                for readout_y, offset, add_ysize in zip(READOUT_Y, OFFSET, ADD_YSIZE)
                ]

        elif mode.startswith('Drift'):
            nx = self.header['ESO DET DRWIN NX'] // xbin
            ny = self.header['ESO DET DRWIN NY'] // ybin
            llxs = [llx + self.header['ESO DET DRWIN XS{}'.format(quad)]
                    for llx, quad in zip(LLX, QUAD)]
            llys = [
                readout_y + offset*self.header['ESO DET DRWIN1 YS'] -
                add_ysize*self.header['ESO DET DRWIN NY']
                for readout_y, offset, add_ysize in zip(READOUT_Y, OFFSET, ADD_YSIZE)
                ]

        else:
            msg = 'mode {} not currently supported'.format(mode)
            raise ValueError(msg)

        # build the Windows
        self.windows = []
        for llx, lly in zip(llxs, llys):
            self.windows.append(Window(llx, lly, nx, ny, xbin, ybin))

        # Build (more) header info
        if 'DATE' in self.header:
            self.thead['DATE'] = (self.header.get('DATE'), self.header.get_comment('DATE'))
        if full and 'ESO DET GPS' in self.header:
            self.thead['GPS'] = (self.header.get('ESO DET GPS'), self.header.get_comment('ESO DET GPS'))

        # Header per CCD
        self.cheads = []
        for n in range(1,6):
            chead = fits.Header()

            # Essential items
            hnam = 'ESO DET NSKIP{:d}'.format(n)
            if hnam in self.header:
                chead['NSKIP'] = (self.header.get(hnam), self.header.get_comment(hnam))

            # Nice if you can get them
            if full:
                # whether this CCD has gone through a reflection
                hnam = 'ESO DET REFLECT{:d}'.format(n)
                if hnam in self.header:
                    chead['REFLECT'] = (self.header.get(hnam), 'is image reflected')

                # readout noise
                hnam = 'ESO DET CHIP{:d} RON'.format(n)
                if hnam in self.header:
                    chead['RONOISE'] = (self.header.get(hnam), self.header.get_comment(hnam))

                # gain
                hnam = 'ESO DET CHIP{:d} GAIN'.format(n)
                if hnam in self.header:
                    chead['GAIN'] = (self.header.get(hnam), self.header.get_comment(hnam))

            self.cheads.append(chead)

        # end of constructor / initialiser

    def __del__(self):
        """Destructor closes the file"""
        self.ffile.close()

    def npix(self):
        """
        Returns number of (binned) pixels per CCD
        """
        np = 0
        for win in self.windows:
            np += win.nx*win.ny
        return np

class Rdata (Rhead):
    """Callable, iterable object to represent HiPERCAM raw data files.

    The idea is to instantiate an Rdata from a HiPERCAM FITS file and then the
    object generated can be used to deliver MCCD objects by specifying a frame
    number e.g.::

      rdat = Rdata('run045.fits')
      fr10 = rdat(10)
      fr11 = rdat()

    reads frame number 10 and then 11 in from 'run045.fits', or sequentially::

      for mccd in Rdata('run045.fits'):
         print('nccd = ',len(mccd))

    which just prints out the number of CCDs from every exposure in the file
    (=5 in all cases),

    """

    def __init__(self, fname, nframe=1, flt=True, server=False):
        """Connects to a raw HiPERCAM FITS file for reading. The file is kept
        open.  The Rdata object can then generate MCCD objects through being
        called as a function or iterator.

        Arguments::

           fname : (string)
              run name, e.g. 'run036'.

           nframe : (int)
              the frame number to read first [1 is the first].

           flt : (bool)
              True for reading data in as floats. This is the default for
              safety, however the data are stored on disk as unsigned 2-byte
              ints. If you are not doing much to the data, and wish to keep
              them in this form for speed and efficiency, then set flt=False.
              This parameter is used when iterating through an Rdata. The
              __call__ method can override it.

           server : (bool)
              True/False for server vs local disk access
        """

        # read the header
        Rhead.__init__(self, fname, server)
        self.nframe = nframe
        self.server = server
        self.flt = flt

    # Want to run this as a context manager
    def __enter__(self):
        return self

    def __exit__(self, *args):
        if not self.server:
            self.fp.close()

    # and as an iterator.
    def __iter__(self):
        return self

    def __next__(self):
        try:
            return self.__call__(flt=self.flt)
        except (HendError, urllib.error.HTTPError):
            raise StopIteration

    def ntotal(self):
        """
        Returns the total number of complete frames
        """
        if self.server:
            raise NotImplementedError('needs HiPERCAM server to be implemented')
        else:
            ntot = self.header['NAXIS3']
        return ntot

    def time(self, nframe=None):
        """Returns timing information of frame nframe (starts from 1). This saves
        effort reading the data in some cases. Once done, it moves to the next
        frame.

        Arguments::

           nframe : (int | None)
              frame number to get, starting at 1. 0 for the last (complete)
              frame. If nframe == None, the current frame will be used.

        See utimer for what gets returned by this. See also Rtime for a class
        dedicated to reading times only.
        """

        if self.server:
            raise NotImplementedError('needs HiPERCAM server to be implemented')
        else:
            raise NotImplementedError('needs HiPERCAM timing info implementing')

    def __call__(self, nframe=None, flt=None):
        """Reads one exposure from the run the :class:`Rdata` is attached
        to. It works on the assumption that the internal file pointer in the
        :class:`Rdata` is positioned at the start of a frame. If `nframe` is
        None, then it will read the frame it is positioned at. If nframe is an
        integer > 0, it will try to read that particular frame; if nframe ==
        0, it reads the last complete frame.  nframe == 1 gives the first
        frame. This returns an MCCD object. It raises an exception if it fails
        to read data.  The data are stored internally as either 4-byte floats
        or 2-byte unsigned ints.

        Arguments::

           nframe : (int)
              frame number to get, starting at 1. 0 for the last (complete)
              frame. 'None' indicates that the next frame is wanted.

           flt : (bool)
              Set True to read data in as floats. The data are stored on disk
              as unsigned 2-byte ints. If you are not doing much to the data,
              and wish to keep them in this form for speed and efficiency,
              then set flt=False. If None then the value used when
              constructing the MCCD will be used.

        Returns an MCCD for ULTRACAM, a CCD for ULTRASPEC.

        Apart from reading the raw bytes, the main job of this routine is to
        divide up and re-package the bytes read into Windats suitable for
        constructing CCD objects.

        """

        if flt is None: flt = self.flt

        if self.server:
            raise NotImplementedError('needs HiPERCAM server access to be implemented')
        else:
            # timing bytes will need to be implemented

            # read data
            if nframe == 0:
                self.nframe = self.ntotal()
            elif nframe is not None:
                self.nframe = nframe

            if self.nframe > self.ntotal():
                self.nframe = 1
                raise HendError('Rdata.__call__: tried to access a frame exceeding the maximum')

            # read in frame, which should be thought of simply as an array of bytes
            frame = self.ffile[0][self.nframe-1,:,:]
            window_size = self.header['NAXIS1'] // 20
            data = as_strided(frame, strides=(8, 2, 40), shape=(5, 4, window_size))

            # Now build up Windats-->CCDs-->MCCD
            ccds = Group()
            cnams = ('1', '2', '3', '4', '5')
            wnams = ('E1', 'F1', 'G1', 'H1')

            for nccd, (cnam, chead) in enumerate(zip(cnams,self.cheads)):
                # now the Windats
                windats = Group()
                for nwin, wnam in enumerate(wnams):
                    win = self.windows[nwin]
                    windats[wnam] = Windat(win, data[nccd, nwin].reshape(win.ny, win.nx))

                # compile the CCD
                ccds[cnam] = CCD(windats, HCM_NXTOT, HCM_NYTOT, chead)

            # and finally the MCCD
            mccd = MCCD(ccds, self.thead)

        self.nframe += 1

        return mccd
