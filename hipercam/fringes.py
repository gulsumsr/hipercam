# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Defines classes to handle de-fringing.
"""

import numpy as np
import json
from abc import ABC, abstractmethod

#from .core import *
#from .group import *

__all__ = ('Fregion',)

class Fregion(ABC):

    """Abstract class to define regions used to measure fringes.

    """

    @abstractmethod
    def apply(self, x, y, mask=None):
        """Computes the pixels to be used for estimating the fringe
        amplitude.

        Arguments::

           x : 2D array
              X-ordinates of pixels

           y : 2D array
              Y-ordinates of pixels

           mask : None | 2D array
              if specified as an input, will be returned modified
              according to the Fregion.

        Returns: 2D logical array showing which pixels are used
        """
        raise NotImplementedError()

    @abstractmethod
    def __repr__(self):
        raise NotImplementedError()

class Circle(Fregion):

    """Defines a circular region for measuring fringes

    """

    def __init__(self, xcen, ycen, radius, add):
        """
        Arguments::

           xcen : float
              X-ordinate of centre of cirle, starting from
              1 at extreme left of CCD, unbinned pixels.

           ycen : float
              Y-ordinate of centre of cirle, starting from
              1 at bottom of CCD, unbinned pixels.

           radius : float
              radius in unbinned pixels

           add : bool
              True to add pixels, False to remove.
        """
        self.xcen = xcen
        self.ycen = ycen
        self.radius = radius
        self.add = add

    def apply(self, x, y, mask=None):
        """Computes the pixels to be used for estimating the fringe
        amplitude.

        Arguments::

           x : 2D array
              X-ordinates of pixels

           y : 2D array
              Y-ordinates of pixels

           mask : None | 2D array
              if specified as an input, this will be modified
              according to the Fregion

        Returns: 2D logical array showing which pixels are used.
        """
        rsq = (x-self.xcen)**2 + (y-self.ycen)**2
        if mask is None:
            if self.add:
                mask = rsq < self.radius**2
            else:
                mask = rsq > self.radius**2
        else:
            if self.add:
                mask |= rsq < self.radius**2
            else:
                mask &= rsq > self.radius**2
        return mask

    def __repr__(self):
        return 'Circle(xcen={!r}, ycen={!r}, radius={!r}, add={!r})'.format(
            self.xcen, self.ycen, self.radius, self.add
        )

#    def copy(self, memo=None):
#        """Returns with a copy of the Aperture"""
#        return Aperture(
#            self.x, self.y, self.rtarg, self.rsky1, self.rsky2,
#            self.ref, self.mask.copy(), self.extra.copy(),
#            self.link
#        )

#    def write(self, fname):
#        """Dumps Aperture in JSON format to a file called fname"""
#        with open(fname,'w') as fp:
#            json.dump(self, cls=_Encoder, indent=2)

#    def toString(self):
#        """Returns Aperture as a JSON-type string"""
#        return json.dumps(self, fp, cls=_Encoder, indent=2)

#    @classmethod
#    def read(cls, fname):
#        """Read from JSON-format file fname"""
#        with open(fname) as fp:
#            aper = json.load(fp, cls=_Decoder)
#        aper.check()
#        return aper

# classes to support JSON serialisation of Aperture objects
class _Encoder(json.JSONEncoder):

    def default(self, obj):

        if isinstance(obj, Aperture):
            return OrderedDict(
                (
                    ('Comment', 'hipercam.Aperture'),
                    ('x', obj.x),
                    ('y', obj.y),
                    ('rtarg', obj.rtarg),
                    ('rsky1', obj.rsky1),
                    ('rsky2', obj.rsky2),
                    ('ref', obj.ref),
                    ('mask', obj.mask),
                    ('extra', obj.extra),
                    ('link', obj.link),
                    )
                )

        return super().default(obj)

class _Decoder(json.JSONDecoder):

    def __init__(self, *args, **kwargs):
        super().__init__(object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, obj):
        # looks out for Aperture objects. Everything else done by default
        if 'rtarg' in obj and 'rsky1' in obj and 'rsky2' in obj and 'link' in obj:
            return Aperture(
                obj['x'], obj['y'], obj['rtarg'], obj['rsky1'], obj['rsky2'],
                obj['ref'], obj['mask'], obj['extra'], obj['link']
            )

        return obj

if __name__ == '__main__':

    c = Circle(200, 250, 10, True)
    print(c)
