import os
import numpy as np
from tvtk.api import tvtk
from scipy.interpolate import griddata
import matplotlib.pyplot as plt
from pandas import *
import nibabel as nib
import matplotlib.cm as cm
import datetime as dt
import os

import nipype.pipeline.engine as pe          # pypeline engine
import nipype.interfaces.freesurfer as fs
import nipype.interfaces.utility as niu
import nipype.interfaces.io as nio

def surfaceWorkflow(model_path, name="Surface"):
    pipeline = pe.Workflow( name=name )
    inputnode = pe.Node(niu.IdentityInterface( fields=['in_roi','surf_id', 'model_id'] ), name='inputnode' )
    tess = pe.Node( fs.MRITessellate( label_value=1, use_real_RAS_coordinates=True ), name='tessellate' )
    smooth = pe.Node( fs.SmoothTessellation(disable_estimates=True), name='smooth' )
    convert = pe.Node( fs.MRIsConvert(out_datatype='vtk'), name='tovtk' )
    ds = pe.Node(nio.DataSink( base_directory=model_path ), name='sinker')
    outputnode = pe.Node( niu.IdentityInterface( fields=['surface'] ), name='outputnode' )
    
    pipeline.connect( [
                        ( inputnode, tess, [ ( 'in_roi' , 'in_file' ) ] )
                       ,( tess, smooth, [ ( 'surface', 'in_file' ) ])
                       ,( smooth, convert, [ ( 'surface', 'in_file' ) ])
                       ,( inputnode, ds, [ ( 'model_id', 'container' ), ('surf_id', 'surf') ])
                       ,( convert, ds, [( 'converted', 'surf.@file' ) ])
                       ,( ds,outputnode, [('out_file','surface') ]) 
                       ])
    return pipeline  


def fixVtk( input_file, output_file, ref_nii ):
    ref = nib.load( ref_nii )
    orig = np.array( ref.get_shape() ) * 0.5
    ac = ref.get_affine()[0:3,0:3]
    
    rotM = np.zeros( shape=ac.shape )
    rotM[0,0] = -1.0
    rotM[1,2] = 1.0
    rotM[2,1] = -1.0
    
    R = np.dot( rotM, ac )
        
    with open( input_file, 'r' ) as f:
        with open( output_file, 'w' ) as w:
            npoints = 0
            pointid = -5
            
            for i,l in enumerate(f):
                if (i==4):
                    s = l.split()
                    npoints = int( s[1] )
                    fmt = np.dtype( s[2] )
                elif( i>4 and pointid<npoints):
                    vert = np.array( [float(x) for x in l.split()] )
                    vert = np.dot( vert, R ) + orig
                    l = '%.9f  %.9f  %.9f\n' % tuple(vert)
                
                w.write( l )
                pointid = pointid + 1
    return True

def GenerateSurface( data, fname, use_smooth=True, spacing=(1.0,1.0,1.0), origin=(0.0,0.0,0.0) ):
    grid = tvtk.ImageData(spacing=spacing, origin=origin, dimensions=data.shape)
    grid.point_data.scalars = data.ravel().astype( np.uint8 )
    grid.point_data.scalars.name = 'scalars'
    iso = tvtk.ImageMarchingCubes(input=grid)
    iso.update()
    contour = iso.output
    if use_smooth:
        vtkmeshclean = tvtk.CleanPolyData( input=iso.output )
        vtkmeshclean.update()
        smooth = tvtk.SmoothPolyDataFilter( input=vtkmeshclean.output, number_of_iterations=20 )
        smooth.update()
        vtkmeshclean2 = tvtk.CleanPolyData( input=smooth.output )
        vtkmeshclean2.update()
        contour = vtkmeshclean2.output
    contour.point_data.scalars = np.ones( np.shape( contour.points )[0] )
    contour.point_data.scalars.name = 'scalars'
    #origin = tuple( (np.array(data.shape).astype(float)) * -0.5 ) # fix new origin to have a nice view in tkmedit 
    vtk2fsa( contour, '%s.asc' % os.path.splitext( fname )[0], origin=origin)
    #w = tvtk.PolyDataWriter(input=contour, file_name=fname )
    #w.write()
    savevtk( contour, fname )
    return contour

def vtk2fsa( vtk, fname, origin=(0.0,0.0,0.0) ):
    ncells = vtk.polys.number_of_cells
    npoints = len( vtk.points )
    nvalues = len( vtk.polys.data )
    cells = np.reshape( vtk.polys.data, ( ncells, int(nvalues/ncells) ) )
    now = dt.datetime.now()
    points = vtk.points + np.array(origin)

    if os.path.exists( fname ):
        os.remove( fname )

    try:
        with open(fname, 'a+') as f:
            f.write( '#!ascii freesurfer mesh generated from vtk - %s, generated on %s\n' % (os.path.basename(fname),now.strftime("%Y-%m-%d %H:%M"))) # Write header
            f.write( '%d %d\n' % ( npoints, ncells ) ) # Write number of vertices and number of faces
            
            for row in points:
                f.write( '%.6f %.6f %.6f 0\n' % tuple(row) )
    
            for row in cells:
                f.write( '%d %d %d 0\n' % tuple( row[1:] ) )
    except Exception as err:
        print err
        return 0

    return 1

def savevtk( vtk, fname, origin=(0.0,0.0,0.0) ):
    ncells = vtk.polys.number_of_cells
    npoints = len( vtk.points )
    nvalues = len( vtk.polys.data )
    cells = np.reshape( vtk.polys.data, ( ncells, int(nvalues/ncells) ) )
    now = dt.datetime.now()
    points = vtk.points + np.array(origin)

    if os.path.exists( fname ):
        os.remove( fname )

    try:
        with open(fname, 'a+') as f:
            f.write( '# vtk DataFile Version 2.0\n' ) # Write identification
            f.write( '%s, generated on %s\n' % (os.path.basename(fname),now.strftime("%Y-%m-%d %H:%M"))) # Write comment (up to 256 chars)
            f.write( 'ASCII\n' )
            f.write( 'DATASET POLYDATA\n' )
            f.write( 'POINTS %d float\n' % npoints ) 
            for row in points:
                f.write( '%.6f %.6f %.6f\n' % tuple(row) )
    
            f.write( 'POLYGONS %d %d\n' % ( ncells, nvalues ) )
            for row in cells:
                f.write( '3 %d %d %d\n' % tuple( row[1:] ) )
    except Exception as err:
        print err
        return 0

    return 1




def FilterMesh(points, sl, zdim, fname=None ):
    lower = sl <= zdim*0.5
#    filtered = np.around( points[(points[:,2]>(sl-0.25)) & (points[:,2]<(sl+0.25))  ] )
    if lower:
        filtered = np.around( points[(points[:,2]<(sl+0.25))])
    else:
        filtered = np.around( points[(points[:,2]>(sl-0.25))])

#    filtered = points[(points[:,2]>(sl-0.25))]
#    filtered = np.array(list(set(tuple(p) for p in filtered)))
    filtered.view('f,f,f').sort(order=['f2'], axis=0)
    uniq = np.array( DataFrame(filtered).drop_duplicates(cols=[0,1],take_last=lower).values )
    if not fname==None:
        mesh = tvtk.PolyData( points=uniq )
        mesh.point_data.scalars = np.zeros( np.shape(uniq)[0], 'f' )
        mesh.point_data.scalars.name = 'scalars'
        w = tvtk.PolyDataWriter(input=mesh, file_name=fname )
        w.write()
    return uniq,lower

def ComputeContourFunction( image, surf, sl, axis=2, fig=None, color='r' ):
    points = np.array(surf.points, dtype=np.float32 )
    if axis==1:
        points[:,[0,1,2]] = points[:,[0,2,1]]
    elif axis==0:
        points[:,[0,1,2]] = points[:,[2,1,0]]

    dim = np.shape( np.swapaxes( image.get_data(), axis, 2 ) )
    dim2d = ( dim[0], dim[1] )
    xi,yi = np.mgrid[0:dim2d[0],0:dim2d[1]] 
    ps,lower = FilterMesh( points, sl, dim[2], 'Model1/test_pandas.vtk' )
    if lower:
        z_level = sl - 0.05
    else:
        z_level = sl + 0.05
    interpolated = griddata( ps[:,[0,1]], ps[:,2] , (xi,yi), method='cubic', fill_value=z_level )
    return interpolated,z_level

def PlotContour( ref_path, surfs, ax=2, sl=50, colors=[ 'b','r','g','y'] ):
    image = nib.load( ref_path )
    sliced = np.swapaxes( image.get_data(), ax, 2)[:,:,sl]
    cs = [ plt.imshow( sliced, cmap = cm.Greys_r ) ]
    
    for i,s in enumerate(surfs):
    	pts,z_level = ComputeContourFunction( image, s, sl, axis=ax )
        cs.append( plt.contour( pts, linewidths=2.5, colors=colors[i], levels=[z_level] ) )
    return cs
