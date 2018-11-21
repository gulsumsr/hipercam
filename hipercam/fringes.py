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

class Rectangle(Fregion):

    """Defines a rectangular region for measuring fringes

    """

    def __init__(self, x1, x2, y1, y2, add):
        """
        Arguments::

           x1 : float
              Left-hand X-ordinate of rectangle, starting from
              1 at extreme left of CCD, unbinned pixels.

           x2 : float
              Right-hand X-ordinate of rectangle, starting from
              1 at extreme left of CCD, unbinned pixels.

           y1 : float
              Lower Y-ordinate of rectangle, starting from
              1 at bottom of CCD, unbinned pixels.

           y2 : float
              Upper Y-ordinate of rectangle, starting from
              1 at bottom of CCD, unbinned pixels.

           add : bool
              True to add pixels, False to remove.
        """
        self.x1 = x1
        self.x2 = x2
        self.y1 = y1
        self.y2 = y2
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
        inside = (x>=self.x1) & (x<=self.x2) & (y>=self.y1) & (y<=self.y2)
        if mask is None:
            if self.add:
                mask = inside
            else:
                mask = ~inside
        else:
            if self.add:
                mask |= inside
            else:
                mask &= ~inside
        return mask

    def __repr__(self):
        return 'Rectangle(x1={!r}, x2={!r}, y1={!r}, y2={!r}, add={!r})'.format(
            self.x1, self.x2, self.y1, self.y2, self.add
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

        if isinstance(obj, Circle):
            return OrderedDict(
                (
                    ('Comment', 'hipercam.fringes.Circle'),
                    ('x', obj.x),
                    ('y', obj.y),
                    ('radius', obj.radius),
                    ('add', obj.add),
                    )
                )

        elif isinstance(obj, Rectangle):
            return OrderedDict(
                (
                    ('Comment', 'hipercam.fringes.Rectangle'),
                    ('x1', obj.x1),
                    ('x2', obj.x2),
                    ('y1', obj.y1),
                    ('y2', obj.y2),
                    ('add', obj.add),
                    )
                )

        return super().default(obj)

class _Decoder(json.JSONDecoder):

    def __init__(self, *args, **kwargs):
        super().__init__(object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, obj):
        # looks out for Aperture objects. Everything else done by default
        if 'Comment' in obj:
            if obj['Comment'] == 'hipercam.fringes.Circle':
                return Circle(
                    obj['x'], obj['y'], obj['radius'], obj['add']
                )

            elif obj['Comment'] == 'hipercam.fringes.Rectangle':
                return Rectangle(
                    obj['x1'], obj['x2'], obj['y1'], obj['y2'], obj['add']
                )

        return obj

if __name__ == '__main__':

    import numpy as np
    import matplotlib.pyplot as plt

    x = np.linspace(1,500,500)
    y = np.linspace(1,500,500)
    X,Y = np.meshgrid(x,y)

    l = []
    l.append(Rectangle(20, 400, 31, 300, True))
    l.append(Circle(200, 250, 10, False))
    l.append(Circle(260, 150, 20, False))
    l.append(Rectangle(200, 450, 310, 400, True))
    mask = None
    for fr in l:
        mask = fr.apply(X,Y,mask)

    extent=(x.min()-0.5,x.max()+0.5,y.min()-0.5,y.max()+0.5)
    plt.imshow(mask,origin='lower',extent=extent)
    plt.show()

