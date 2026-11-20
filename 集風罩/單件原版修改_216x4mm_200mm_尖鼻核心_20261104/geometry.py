"""Geometry-only parameters for the user's one-piece revision, in mm."""
import math
H=200.
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
    q=ease((z-12)/176);return 82+134*q,88-145.8048780487805*q+61.8048780487805*q*q,3*(1-q)
def core_radii(z):
    if z<12 or z>126:return 0.,0.
    if z<=58:
        q=smooth((z-12)/46);return .6+17.4*q,.6+20.4*q
    return 18-17.4*smooth((z-58)/68),21-20.4*smooth((z-58)/52)
def thickness(z,end):
    if z<0 or z>end:return 0.
    return .8+1.2*min(smooth(z/12),1-smooth((z-end+12)/12))
def net_area(z):
    w,d,r=section(z);rx,ry=core_radii(z);ty=thickness(z,144);tx=thickness(z,134)
    gross=w*d-(4-math.pi)*r*r;cross=w*ty+d*tx-tx*ty;extra=0.
    a,b=tx/2,ty/2
    if rx>a and ry>b:
        top=ry*math.sqrt(max(0,1-(a/rx)**2))
        def integral(y):
            t=max(0,min(1,y/ry));return rx*ry/2*(math.asin(t)+t*math.sqrt(max(0,1-t*t)))
        if top>b:extra=4*(integral(top)-integral(b)-a*(top-b))
    return {'z_mm':z,'width_mm':w,'depth_mm':d,'core_rx_mm':rx,'core_ry_mm':ry,'net_air_area_mm2':gross-cross-extra}
