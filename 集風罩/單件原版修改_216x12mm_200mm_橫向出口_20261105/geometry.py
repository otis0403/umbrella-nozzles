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
    if z<12 or z>126:return 0.,0.
    if z<=58:
        q=smooth((z-12)/46);return .6+17.4*q,.6+20.4*q
    return 18-17.4*smooth((z-58)/68),21-20.4*smooth((z-58)/52)
def thickness(z,end):
    if z<0 or z>end:return 0.
    return .8+1.2*min(smooth(z/12),1-smooth((z-end+12)/12))
def net_area(z):
    w,d,r=section(z);ru,rv=core_radii_uv(z);tu=thickness(z,134);tv=thickness(z,144)
    gross=w*d-(4-math.pi)*r*r;cross=w*tv+d*tu-tu*tv;extra=0.
    a,b=tu/2,tv/2
    if ru>a and rv>b:
        top=rv*math.sqrt(max(0,1-(a/ru)**2))
        def integral(v):
            t=max(0,min(1,v/rv));return ru*rv/2*(math.asin(t)+t*math.sqrt(max(0,1-t*t)))
        if top>b:extra=4*(integral(top)-integral(b)-a*(top-b))
    return {'z_mm':z,'u_width_mm':w,'v_depth_mm':d,'corner_radius_mm':r,'core_u_radius_mm':ru,'core_v_radius_mm':rv,
        'gross_area_mm2':gross,'occupied_area_mm2':cross+extra,'net_air_area_mm2':gross-cross-extra}

HOLES=[{'x_mm':2+dz,'y_mm':dy,'diameter_mm':6.4 if abs(dy)==51 and abs(dz)==50 else 4.4}
    for dy,dz in [(-51,50),(51,50),(-51,-50),(51,-50),(-25,50),(25,50),(-25,-50),(25,-50),(-51,-25),(-51,25),(51,-25),(51,25)]]
