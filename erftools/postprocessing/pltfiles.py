import numpy as np
import xarray as xr
import yt


xyz = ['x','y','z']

class Plotfile(object):
    """Process cell-centered volume data"""

    def __init__(self,fpath,verbose=False,*args,**kwargs):
        self.verbose = verbose
        if verbose:
            yt.set_log_level('info')
        else:
            yt.set_log_level('error')

        self.pf = yt.load(fpath, *args, **kwargs)
        self.fields = [fld for (typ,fld) in self.pf.field_list if typ=='boxlib']

        # 1-D cordinate arrays
        self.coords1d = [None,None,None] # x1, y1, z1

        # initialize slicing data
        self.slc_coords = [None,None,None] # yz, xz, xy planes
        self.slc_order = [None,None,None]
        self.slc_shape = [None,None,None]

    def slice(self, axis, loc, fields=None):
        """Create cutplane through the volume at index closest to the
        requested location

        Parameters
        ----------
        axis : int
            Slice orientation (x=0, y=1, z=2)
        loc : float
            Slice location
        """
        slc = self.pf.slice(axis, loc)
        actual_loc = slc.fcoords[0,axis]
        assert np.all(slc.fcoords[:,axis] == actual_loc)
        if self.verbose:
            print('Slice at',xyz[axis],'=',slc.fcoords[0,axis].value)
        slc_dims = [idim for idim in range(3) if idim != axis]

        if self.slc_coords[axis] is None:
            # process sliced coordinates
            coords = np.stack([slc.fcoords[:,idim].value for idim in slc_dims], axis=-1)
            order = np.lexsort((coords[:,1],coords[:,0]))
            shape = tuple(self.pf.domain_dimensions[idim] for idim in slc_dims)
            coords2d_0 = coords[order,0].reshape(shape)
            coords2d_1 = coords[order,1].reshape(shape)
            array_0 = coords2d_0[:,0]
            array_1 = coords2d_1[0,:]
            # set or check 1-D coordinate arrays
            if self.coords1d[slc_dims[0]] is None:
                if self.verbose:
                    print('Setting',xyz[slc_dims[0]],'coord')
                self.coords1d[slc_dims[0]] = array_0
            else:
                assert np.all(array_0 == self.coords1d[slc_dims[0]])
            if self.coords1d[slc_dims[1]] is None:
                if self.verbose:
                    print('Setting',xyz[slc_dims[1]],'coord')
                self.coords1d[slc_dims[1]] = array_1
            else:
                assert np.all(array_1 == self.coords1d[slc_dims[1]])
            self.slc_coords[axis] = coords
            self.slc_order[axis] = order
            self.slc_shape[axis] = shape

        # create an xarray dataset for the slice
        dimnames = tuple(xyz[idim] for idim in slc_dims)
        dimcoords = [self.coords1d[idim] for idim in slc_dims]
        if fields is None:
            fieldlist = self.fields
        elif isinstance(fields, str):
            fieldlist = [fields]
        else:
            fieldlist = fields
        sliceflds = {}
        for fld in fieldlist:
            fld1 = slc[fld].value[self.slc_order[axis]]
            fld2 = fld1.reshape(self.slc_shape[axis])
            sliceflds[fld] = (dimnames, fld2)
        ds = xr.Dataset(sliceflds, coords=dict(zip(dimnames, dimcoords)))
        ds = ds.expand_dims({xyz[axis]: [actual_loc]})

        return ds.transpose('x','y','z')


