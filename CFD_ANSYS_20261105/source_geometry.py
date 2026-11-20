"""Millimetre geometry. U=outlet long direction, V=outlet short direction.

Fixed flange coordinates are X,Y,Z. New upper duct: (X,Y,Z)=(-V,U,Z).
This rotates the long outlet relative to the flange, not the flow axis.
"""
import math
H,NECK,TRANSITION,LIP,WALL=200.,12.,176.,12.,2.
def smooth(t):
    t=max(0.,min(1.,t));return t*t*t*(10+t*(-15+6*t))
def ease(t):
    t=max(0.,min(1.,t));b=.2
    if t<=b:
        u=t/b;return b*(u**3-.5*u**4)/(1-b)
    if t>=1-b:
        u=(1-t)/b;return 1-b*(u**3-.5*u**4)/(1-b)
    return (t-b/2)/(1-b)
def section(z):
    q=ease((z-NECK)/TRANSITION)
    return 88+128*q,82-120*q+50*q*q,3*(1-q)
def local_to_global(u,v,z):return (-v,u,z)
def core_radii_uv(z):
    # This variant deliberately has no central fairing. Vanes remain.
    return 0.,0.
def thickness(z,end):
    if z<0 or z>end:return 0.
    return .8+1.2*min(smooth(z/12),1-smooth((z-end+12)/12))
def net_area(z):
    w,d,r=section(z);tu=thickness(z,134);tv=thickness(z,144)
    gross=w*d-(4-math.pi)*r*r;cross=w*tv+d*tu-tu*tv
    return {'z_mm':z,'u_width_mm':w,'v_depth_mm':d,'corner_radius_mm':r,'core_u_radius_mm':0.,'core_v_radius_mm':0.,
        'gross_area_mm2':gross,'occupied_area_mm2':cross,'net_air_area_mm2':gross-cross}

HOLES=[{'x_mm':2+dz,'y_mm':dy,'diameter_mm':6.4 if abs(dy)==51 and abs(dz)==50 else 4.4}
    for dy,dz in [(-51,50),(51,50),(-51,-50),(51,-50),(-25,50),(25,50),(-25,-50),(25,-50),(-51,-25),(-51,25),(51,-25),(51,25)]]
