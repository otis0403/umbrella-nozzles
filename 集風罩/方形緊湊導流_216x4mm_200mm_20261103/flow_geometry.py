"""Transparent geometry/energy calculations, not CFD or a fan prediction."""
from pathlib import Path
import math,json,csv
HERE=Path(__file__).resolve().parent
W,GAP,NECK,LIP=216.,4.,12.,12.
B=145.8048780487805
C=B-88+GAP

def smooth(t):
    t=max(0.,min(1.,t));return t*t*t*(10+t*(-15+6*t))

def ease(t):
    t=max(0.,min(1.,t));b=.2
    if t<=b:
        u=t/b;return b*(u**3-.5*u**4)/(1-b)
    if t>=1-b:
        u=(1-t)/b;return 1-b*(u**3-.5*u**4)/(1-b)
    return (t-b/2)/(1-b)

def ease_derivative(t):
    if not 0<t<1:return 0.
    u=min(t,1-t)/.2
    return (3*u*u-2*u*u*u)/.8 if u<1 else 1.25

def section(z,h=200):
    t=ease((z-NECK)/(h-NECK-LIP))
    return 82+134*t,88-B*t+C*t*t,3*(1-t)

def core_radii(z,h=200):
    peak=.29*h;end=.63*h;yend=.55*h
    if z<12 or z>end:return 0.,0.
    if z<=peak:
        r=.6+17.4*smooth((z-12)/(peak-12));return r,r
    return 18-17.4*smooth((z-peak)/(end-peak)),18-17.4*smooth((z-peak)/(yend-peak))

def vane_thickness(z,end):
    if z<12 or z>end:return 0.
    return .8+1.2*min(smooth((z-12)/10),1-smooth((z-end+12)/12))

def net_area(z,h=200):
    w,d,r=section(z,h);rx,ry=core_radii(z,h)
    ty=vane_thickness(z,.72*h);tx=vane_thickness(z,.67*h)
    gross=w*d-(4-math.pi)*r*r
    cross=w*ty+d*tx-tx*ty;extra=0.
    a,b=tx/2,ty/2
    if rx>a and ry>b:
        top=ry*math.sqrt(max(0,1-(a/rx)**2))
        def primitive(y):
            t=max(0,min(1,y/ry))
            return rx*ry/2*(math.asin(t)+t*math.sqrt(max(0,1-t*t)))
        if top>b:extra=4*(primitive(top)-primitive(b)-a*(top-b))
    return {'z_mm':z,'width_mm':w,'depth_mm':d,'core_rx_mm':rx,'core_ry_mm':ry,
        'vane_y_thickness_mm':ty,'vane_x_thickness_mm':tx,'gross_area_mm2':gross,
        'occupied_area_mm2':cross+extra,'net_air_area_mm2':gross-cross-extra}

def study(h):
    points=[net_area(h*j/2000,h) for j in range(2001)]
    inlet=net_area(0,h)['net_air_area_mm2'];outlet=points[-1]['net_air_area_mm2']
    maxflare=maxcontract=maxcorner=0.
    for j in range(10001):
        t=j/10000;q=ease(t);dq=ease_derivative(t)/(h-24)
        sx=67*dq;sy=abs((-B+2*C*q)*dq/2)
        maxflare=max(maxflare,math.degrees(math.atan(sx)))
        maxcontract=max(maxcontract,math.degrees(math.atan(sy)))
        maxcorner=max(maxcorner,math.degrees(math.atan(math.hypot(sx,sy))))
    clearance=min(p['depth_mm']/2-p['core_ry_mm'] for p in points if p['core_rx_mm']>0)
    assert clearance>1
    minimum=min(points,key=lambda p:p['net_air_area_mm2'])
    assert minimum['net_air_area_mm2']>=864-1e-7
    return {'total_height_mm':h,'transition_length_mm':h-24,'outer_envelope_mm':[220,120,h],
        'maximum_wide_wall_flare_deg':maxflare,'maximum_thin_wall_contraction_deg':maxcontract,
        'maximum_corner_path_angle_estimate_deg':maxcorner,
        'minimum_net_area_mm2':minimum['net_air_area_mm2'],'minimum_area_at_Z_mm':minimum['z_mm'],
        'input_free_area_mm2':inlet,'inlet_unobstructed':True,'area_ratio_inlet_to_outlet':inlet/outlet,
        'minimum_core_to_front_back_wall_clearance_mm':clearance,
        'maximum_upstream_local_area_increase_per_sample_mm2':max(b['net_air_area_mm2']-a['net_air_area_mm2'] for a,b in zip(points,points[1:])),
        'core_start_peak_end_mm':[12,.29*h,.63*h],'core_max_diameter_mm':36,
        'guide_end_Z_mm':[.72*h,.67*h],'remaining_unpartitioned_length_mm':h-.72*h,
        'angle_note':'Geometry comparison only; no universal separation threshold is assumed',
        'cross_section_samples':points}

def main():
    variants=[study(h) for h in [180.,200.,220.,240.]]
    chosen=variants[1]
    rho=1.2;ai=chosen['input_free_area_mm2']*1e-6;ao=864e-6
    energy=[]
    for q in [.5,1.,1.5]:
        vi=q/60/ai;vo=q/60/ao
        energy.append({'specified_flow_m3_per_min':q,'inlet_mean_speed_m_per_s':vi,'outlet_mean_speed_m_per_s':vo,
            'outlet_velocity_pressure_Pa':.5*rho*vo*vo,'ideal_inlet_to_outlet_static_pressure_drop_Pa':.5*rho*(vo*vo-vi*vi)})
    result={'date':'2026-11-03','units':'mm','source_interface_mm':[82,88],'inlet_corner_radius_mm':3,
        'outlet_mm':[216,4],'outlet_area_mm2':864,'selected_height_mm':200,
        'selection_reason':'Compact intermediate geometry candidate: 180 mm has steeper wall turning; not an optimum or validated minimum',
        'design':'Pointed nose, tapered core and orthogonal thin vanes; rectangular direct connection; no round adapter',
        'variants':variants,'energy_examples':energy,'air_density_assumption_kg_m3':rho,
        'energy_note':'Prescribed Q examples only. Bernoulli ideal acceleration term excludes all losses and does not establish the fan operating point. The 460 Pa and 11 m3/min label values are not treated as simultaneous or a full fan curve.',
        'compared_to_previous_round_envelope_mm':[224,184,328],
        'envelope_reductions_fraction':{'depth':1-120/184,'height':1-200/328,'bounding_volume':1-(220*120*200)/(224*184*328)},
        'status':{'CFD':False,'measured_PQ_curve':False,'print_test':False,'flow_or_backflow_guaranteed':False},
        'references':['https://patents.google.com/patent/US20170006991A1/en','https://www.amca.org/educate/articles-and-technical-papers/amca-inmotion-articles/straightening-out-fan-curves.html']}
    (HERE/'尺寸方案計算.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    keys=['total_height_mm','transition_length_mm','maximum_wide_wall_flare_deg','maximum_thin_wall_contraction_deg','maximum_corner_path_angle_estimate_deg','minimum_net_area_mm2','minimum_core_to_front_back_wall_clearance_mm','remaining_unpartitioned_length_mm']
    with (HERE/'長度方案比較.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader();writer.writerows([{k:v[k] for k in keys} for v in variants])
    print(json.dumps({'variants':[{k:v[k] for k in keys} for v in variants],'energy':energy,'inlet_free_area':chosen['input_free_area_mm2']},ensure_ascii=False))

if __name__=='__main__':main()
