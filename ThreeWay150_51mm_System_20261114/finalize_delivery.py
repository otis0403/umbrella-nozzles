"""Package only selected parts and validated fixed-16 mm results."""
import csv,hashlib,json,math,subprocess,sys,zipfile,shutil
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.font_manager import FontProperties
from matplotlib.patches import FancyBboxPatch,FancyArrowPatch
from PIL import Image,ImageDraw,ImageFont
from geometry import ROOT,port
from analyze import convergence,jet_metrics

def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def write(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def make_plate(geo):
    part=next(r for r in geo['parts'] if r['group']=='nozzle');p=ROOT/'print/3MF'/(part['name']+'.3mf')
    ns={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'};ET.register_namespace('',ns['m'])
    with zipfile.ZipFile(p) as z:files={n:z.read(n) for n in z.namelist()}
    model=ET.fromstring(files['3D/3dmodel.model']);build=model.find('m:build',ns)
    for item in list(build):build.remove(item)
    for x in [45,110,175]:ET.SubElement(build,'{'+ns['m']+'}item',objectid='1',transform=f'1 0 0 0 1 0 0 0 1 {x} 110 0')
    width,span,height=part['print_size_mm'];assert width+10<=65 and span+10<=220 and height<=250
    files['3D/3dmodel.model']=ET.tostring(model,encoding='utf-8',xml_declaration=True)
    out=ROOT/'print/3MF/nozzles_quantity3_K1C.3mf'
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for n,v in files.items():z.writestr(n,v)
    with zipfile.ZipFile(out) as z:
        assert z.testzip() is None
        reread=ET.fromstring(z.read('3D/3dmodel.model'))
    vertices=np.array([[float(v.get(k)) for k in ['x','y','z']] for v in reread.findall('m:resources/m:object/m:mesh/m:vertices/m:vertex',ns)])
    items=reread.findall('m:build/m:item',ns);assert len(items)==3
    for item in items:
        transform=np.array([float(v) for v in item.get('transform').split()]).reshape(4,3)
        actual=vertices@transform[:3]+transform[3]
        assert (actual[:,:2].min(0)>=5).all() and (actual[:,:2].max(0)<=215).all() and actual[:,2].min()>=0 and actual[:,2].max()<=250
    write(ROOT/'print/three_nozzle_plate_checks.json',dict(items=3,centers_X_mm=[45,110,175],minimum_model_gap_mm=65-width,within_K1C_with_5mm_brim=True,individual_5mm_brims_do_not_overlap=True,
        independently_reopened_all_build_items=True,generic_3MF_geometry_only=True,actual_slicing_verified=False))

def polys(data,axes=(0,1)):
    return [data['vertices'][data['indices'][data['offsets'][i]:data['offsets'][i+1]]][:,axes]*1000 for i in range(len(data['offsets'])-1)]

def figures(sel,geo,rows,metrics):
    labels=['50 / 70 cm','60 / 80 cm','100 / 120 cm'];x=np.arange(3)
    fig,axes=plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
    for k,label in enumerate(['Left','Center','Right']):axes[0].bar(x+(k-1)*.23,[r['flows'][k] for r in rows],width=.23,label=label)
    axes[0].set(xticks=x,xticklabels=labels,ylabel='Per-head flow (m3/min)',title='Physical hose lengths: center / sides');axes[0].legend()
    bars=axes[1].bar(x,[r['total'] for r in rows],color=['#168998','#3c8494','#6a7c8a'])
    for bar,row in zip(bars,rows):axes[1].text(bar.get_x()+bar.get_width()/2,bar.get_height()+.03,f"{row['total']:.3f}",ha='center')
    axes[1].set(xticks=x,xticklabels=labels,ylabel='Total flow (m3/min)',title='Three 150 x 16 mm nozzles')
    fig.suptitle('Fluent + equivalent hose resistance; hypothetical inlet TOTAL pressure 400 Pa')
    fig.savefig(ROOT/'images/CFD_pipe_length_comparison.png',dpi=180);plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(14,4.4),layout='constrained')
    for key,label in zip(['50_70','60_80','100_120'],labels):
        case=sel['jet_cases'][key]
        for ax,d in zip(axes,[30,50,80]):
            a=np.loadtxt(ROOT/'cfd'/case/f'profile_{d}mm.csv',delimiter=',',skiprows=1);ax.plot(a[:,0],a[:,1],label=label)
            ax.set(xlabel='Y across outlet (mm)',ylabel='Uz at X=0 (m/s)',title=f'{d} mm after outlet');ax.grid(alpha=.2)
    axes[1].legend(fontsize=8);fig.suptitle('Weakest branch per pipe configuration; same 150 x 16 mm outlet')
    fig.savefig(ROOT/'images/CFD_outlet_profiles.png',dpi=180);plt.close(fig)
    data=np.load(ROOT/'cfd'/sel['fine_adapter_case']/'cut_fields.npz');value=np.sqrt(data['x-velocity']**2+data['y-velocity']**2+data['z-velocity']**2)
    xyz=data['centroids']*1000;mask=np.ones(len(xyz),bool)
    for k in range(3):
        E,D=port(k,sel['adapter_height_mm']);a=(xyz-E)@D;radial=np.linalg.norm(xyz-E-a[:,None]*D,axis=1);mask&=~((a>25)&(radial<23.1))
    polygons=polys(data,(0,2));fig,ax=plt.subplots(figsize=(7,5.5),layout='constrained');collection=PolyCollection([p for p,m in zip(polygons,mask) if m],array=value[mask],cmap='turbo',edgecolors='none')
    ax.add_collection(collection);ax.autoscale_view();ax.set(aspect='equal',xlabel='X (mm)',ylabel='Z from flange (mm)',title='Actual Fluent adapter section at Y=1 mm');fig.colorbar(collection,ax=ax,label='Speed (m/s)')
    fig.savefig(ROOT/'images/CFD_adapter_flow_section.png',dpi=180);plt.close(fig)
    fig,axes=plt.subplots(3,1,figsize=(11,7),layout='constrained')
    for ax,key,label in zip(axes,['50_70','60_80','100_120'],labels):
        data=np.load(ROOT/'cfd'/sel['jet_cases'][key]/'plane_80mm_fields.npz');collection=PolyCollection(polys(data,(1,0)),array=data['z-velocity'],cmap='turbo',edgecolors='none',clim=(0,22))
        ax.add_collection(collection);ax.set(xlim=(-95,95),ylim=(-35,35),aspect='equal',xlabel='Y (mm)',ylabel='X (mm)',title=f'80 mm after outlet: {label}')
    fig.colorbar(collection,ax=list(axes),label='Uz (m/s)',shrink=.8);fig.savefig(ROOT/'images/CFD_80mm_velocity_maps.png',dpi=180);plt.close(fig)
    font=ImageFont.truetype('C:/Windows/Fonts/msjh.ttc',34);small=ImageFont.truetype('C:/Windows/Fonts/msjh.ttc',25)
    canvas=Image.new('RGB',(1600,1110),'#eef3f5');draw=ImageDraw.Draw(canvas)
    draw.text((35,20),'51 mm軟管三路接頭 ＋ 150×16 mm直線吹嘴',font=font,fill='#193441')
    for j,kind in enumerate(['adapter','nozzle']):
        photo=Image.open(ROOT/'images'/f'CAD_{kind}.png').convert('RGB');photo.thumbnail((760,800));canvas.paste(photo,(j*800+20,85))
        part=next(r for r in geo['parts'] if r['group']==kind);size=part['print_size_mm']
        draw.text((j*800+35,910),'三路接頭：列印1個' if kind=='adapter' else '同款吹嘴：列印3個',font=font,fill='#193441')
        draw.text((j*800+35,967),f"外形約 {size[0]:.1f}×{size[1]:.1f}×{size[2]:.0f} mm",font=small,fill='#193441')
        draw.text((j*800+35,1010),'插管端外徑50 mm、內徑46 mm、套入25 mm',font=small,fill='#193441')
    draw.text((35,1060),'實際CAD模型預覽；尚未實印或驗證吹乾時間。',font=small,fill='#51636d');canvas.save(ROOT/'images/Design_overview.png')
    fp=FontProperties(fname='C:/Windows/Fonts/msjh.ttc')
    fig,ax=plt.subplots(figsize=(11,6),layout='constrained');ax.set(xlim=(-3,3),ylim=(-1.2,4));ax.axis('off')
    for x,label in [(-2,'左吹嘴'),(0,'中吹嘴'),(2,'右吹嘴')]:
        ax.add_patch(FancyBboxPatch((x-.75,2.7),1.5,.45,boxstyle='round,pad=.02',facecolor='#d7e7ed',edgecolor='#193441'))
        ax.text(x,2.92,label+' 150×16 mm',ha='center',va='center',fontproperties=fp,fontsize=11)
        ax.annotate('',xy=(x,3.65),xytext=(x,3.18),arrowprops=dict(arrowstyle='->',color='#168998',lw=2))
        origin=(x*.22,.95);end=(x,2.65)
        ax.add_patch(FancyArrowPatch(origin,end,connectionstyle=f'arc3,rad={-.12 if x<0 else .12 if x>0 else 0}',arrowstyle='-',lw=8,color='#a6b8c3'))
        ax.text(x*.8,1.75,'中管 L' if x==0 else '側管 L＋20 cm',ha='center',fontproperties=fp,fontsize=11)
    ax.add_patch(FancyBboxPatch((-.8,.2),1.6,.65,boxstyle='round,pad=.02',facecolor='#91cbd0',edgecolor='#193441'));ax.text(0,.53,'三路接頭',ha='center',va='center',fontproperties=fp,fontsize=13)
    ax.add_patch(FancyBboxPatch((-.8,-.65),1.6,.6,boxstyle='round,pad=.02',facecolor='#d0d6db',edgecolor='#193441'));ax.text(0,-.35,'原鼓風機與12孔法蘭',ha='center',va='center',fontproperties=fp,fontsize=12)
    ax.plot([0,0],[-.05,.2],color='#193441',lw=3)
    ax.text(0,-1.0,'兩端各套入25 mm，以6個管夾固定；位置為示意，非機殼安裝座標。',ha='center',fontproperties=fp,fontsize=11)
    ax.set_title('一台鼓風機：接頭1個＋相同吹嘴3個',fontproperties=fp,fontsize=16)
    fig.savefig(ROOT/'images/Assembly_schematic.png',dpi=180);plt.close(fig)

def main():
    sel=read(ROOT/'final_selection.json');geo=read(ROOT/'cad/geometry_checks.json');cv=convergence()
    report_cases=sel['validation_cases']+sel.get('diagnostic_cases',[])
    assert geo['nozzle_gap_mm']==16 and geo['adapter_height_mm']==sel['adapter_height_mm'] and geo['nozzle_length']==sel['nozzle_length_mm']
    assert all(cv[n]['engineering_convergence_pass'] for n in sel['validation_cases']),[(n,cv[n]) for n in sel['validation_cases'] if not cv[n]['engineering_convergence_pass']]
    assert read(ROOT/'cad/native_reopen_checks.json')['native_blend_reopened']
    airway=read(ROOT/'cad/airpath_checks.json');nozzle_check=next(r for r in airway if r['part']=='nozzle')
    assert all(abs(v-16)<.025 for v in nozzle_check['gap_range_mm']) and abs(nozzle_check['clear_span_mm']-150)<.025
    native=read(ROOT/'native_reopen_checks.json');assert all(r['native_case_data_reopened'] for r in native)
    rows=[];metrics={};area=(150*16-(4-math.pi)*.8**2)*1e-6
    for key,center,side in [('50_70',.5,.7),('60_80',.6,.8),('100_120',1.,1.2)]:
        r=read(ROOT/'cfd'/sel['pipe_cases'][key]/'results.json');assert r['network_load_consistency_pass'] and abs(r['reports']['ptin']-400)<1e-5;m=jet_metrics(sel['jet_cases'][key]);metrics[key]=m
        rows.append(dict(configuration=key,physical_center_m=center,physical_sides_m=side,effective_center_m=center-.05,effective_sides_m=side-.05,
            flows=r['branch_flow_m3_min'],total=r['total_flow_m3_min'],balance=r['balance_error_pct'],speeds=(np.array(r['branch_flow_m3_min'])/60/area).tolist(),loss=r['adapter_total_pressure_loss_Pa']))
    baseline_balance=max(r['balance'] for r in rows)
    sensitivity_balance=max(read(ROOT/'cfd'/n/'results.json')['balance_error_pct'] for n in sel['sensitivity_cases'])
    assert baseline_balance<=5 and sensitivity_balance<=10,('Branch balance target unresolved',baseline_balance,sensitivity_balance)
    a=read(ROOT/'cfd'/sel['pipe_cases']['100_120']/'results.json');b=read(ROOT/'cfd'/sel['fine_adapter_case']/'results.json')
    assert b['network_load_consistency_pass']
    fine_adapter=dict(total_flow_change_pct=100*(b['total_flow_m3_min']/a['total_flow_m3_min']-1),maximum_share_change_percentage_points=float(max(abs(np.array(b['branch_share_pct'])-np.array(a['branch_share_pct'])))),
        method='Finer O-grid with changed topology; not GCI')
    assert abs(fine_adapter['total_flow_change_pct'])<3 and fine_adapter['maximum_share_change_percentage_points']<1
    mf=jet_metrics(sel['fine_jet_case']);ms=metrics['100_120'];fine_jet={}
    actual_maximum_cv=max(m[f'{d}mm']['core_140mm_line_CV_pct'] for m in list(metrics.values())+[mf] for d in [30,50,80])
    fine_converged=cv.get(sel['fine_jet_case'],{}).get('engineering_convergence_pass',False)
    sel['maximum_nozzle_CV_pct']=actual_maximum_cv;sel['nozzle_uniformity_target_met']=fine_converged and actual_maximum_cv<=10;write(ROOT/'final_selection.json',sel)
    write(ROOT/'design_acceptance.json',dict(outlet_clear_span_mm=150,outlet_clear_gap_mm=16,
        baseline_maximum_branch_balance_error_pct=baseline_balance,baseline_under_5pct=True,
        sensitivity_maximum_branch_balance_error_pct=sensitivity_balance,sensitivity_under_10pct=True,
        maximum_nozzle_line_CV_pct=actual_maximum_cv,nozzle_line_CV_under_10pct=fine_converged and actual_maximum_cv<=10,fine_nozzle_converged=fine_converged,
        nozzle_uniformity_is_a_design_target_not_a_physical_test=True,physical_drying_test_complete=False))
    for d in [30,50,80]:
        k='same_140x20_patch_mean_normal_dynamic_pressure_Pa';fine_jet[f'{d}mm_normalized_dynamic_pressure_change_pct']=100*((mf[f'{d}mm'][k]/mf['Q_m3_min']**2)/(ms[f'{d}mm'][k]/ms['Q_m3_min']**2)-1)
    fine_jet['required_total_pressure_normalized_change_pct']=100*((read(ROOT/'cfd'/sel['fine_jet_case']/'results.json')['reports']['ptin']/mf['Q_m3_min']**2)/(read(ROOT/'cfd'/sel['jet_cases']['100_120']/'results.json')['reports']['ptin']/ms['Q_m3_min']**2)-1)
    velocity_sensitivity_pass=max(abs(fine_jet[f'{d}mm_normalized_dynamic_pressure_change_pct']) for d in [30,50,80])<5
    pressure_sensitivity_pass=abs(fine_jet['required_total_pressure_normalized_change_pct'])<5
    fine_jet['dynamic_pressure_target_under_5pct']=velocity_sensitivity_pass
    fine_jet['required_total_pressure_target_under_5pct']=pressure_sensitivity_pass
    fine_jet['fine_case_engineering_converged']=fine_converged
    fine_jet['evaluation_status']='converged_combined_sensitivity' if fine_converged else 'diagnostic_only_fine_case_not_converged'
    fine_jet['all_5pct_targets_met']=fine_converged and velocity_sensitivity_pass and pressure_sensitivity_pass
    fine_jet['method']='Finer O-grid plus downstream open-domain length 250 to 400 mm; combined sensitivity, not GCI'
    write(ROOT/'mesh_sensitivity_checks.json',dict(adapter=fine_adapter,nozzle=fine_jet))
    acceptance=read(ROOT/'design_acceptance.json')
    acceptance['all_nozzle_mesh_sensitivity_targets_met']=fine_jet['all_5pct_targets_met']
    acceptance['release_status']='printable_prototype_with_reported_numerical_limits' if not (fine_jet['all_5pct_targets_met'] and sel['nozzle_uniformity_target_met']) else 'numerically_checked_printable_prototype'
    write(ROOT/'design_acceptance.json',acceptance)
    make_plate(geo);figures(sel,geo,rows,metrics)
    from dimension_drawing import draw_dimensions
    drawing=ROOT/'images/CAD_dimension_checks.png'
    if not drawing.exists() or drawing.stat().st_mtime<(ROOT/'cad/geometry_checks.json').stat().st_mtime:draw_dimensions(geo)
    start=read(ROOT/'original_sources.json');source=Path(start['source']);now={k:digest(source/k) for k in start['files']};assert now==start['files']
    write(ROOT/'source_integrity.json',dict(all_original_files_unchanged=True,file_count=len(now),files=now))
    columns=['configuration','physical_center_m','physical_sides_m','effective_center_m','effective_sides_m','left_m3_min','center_m3_min','right_m3_min','total_m3_min','max_balance_error_pct','left_mean_exit_m_s','center_mean_exit_m_s','right_mean_exit_m_s','adapter_total_pressure_loss_Pa']
    with (ROOT/'pipe_length_comparison.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(columns)
        for r in rows:w.writerow([r['configuration'],r['physical_center_m'],r['physical_sides_m'],r['effective_center_m'],r['effective_sides_m'],*r['flows'],r['total'],r['balance'],*r['speeds'],r['loss']])
    parts={r['group']:r for r in geo['parts']};table='\n'.join(f"| {r['physical_center_m']*100:g}／{r['physical_sides_m']*100:g} | {r['flows'][0]:.3f} | {r['flows'][1]:.3f} | {r['flows'][2]:.3f} | {r['total']:.3f} | {r['balance']:.2f}% | {min(r['speeds']):.2f}–{max(r['speeds']):.2f} |" for r in rows)
    jettable='\n'.join(f"| {key} | {d/10:g} | {metrics[key][f'{d}mm']['core_line_mean_Uz_m_s']:.2f} | {metrics[key][f'{d}mm']['core_140mm_line_CV_pct']:.2f}% | {metrics[key][f'{d}mm']['same_140x20_patch_mean_normal_dynamic_pressure_Pa']:.2f} | {metrics[key][f'{d}mm']['same_140x80_strip_momentum_N']:.4f} |" for key in ['50_70','60_80','100_120'] for d in [30,50,80])
    improvement50=100*(rows[0]['total']/rows[2]['total']-1);improvement60=100*(rows[1]['total']/rows[2]['total']-1);difference=100*(rows[0]['total']/rows[1]['total']-1)
    convtable='\n'.join(f"| {n} | {cv[n]['iteration']} | {cv[n]['residuals']['continuity']:.3g} | {cv[n]['mass_imbalance_pct']:.3g} | {'通過' if cv[n]['engineering_convergence_pass'] else '未通過，僅診斷'} | {'是' if cv[n]['strict_all_residuals_under_1e_minus_5'] else '否'} |" for n in report_cases)
    shape=read(ROOT/'selected_shape_work.json');target_text='達到' if sel.get('nozzle_uniformity_target_met') else '尚未完全達到'
    report=f'''# 51 mm軟管三路接頭與150×16 mm吹嘴

2026-11-14。單台鼓風機使用接頭1個、相同吹嘴3個、管夾6個。出口固定150×16 mm，氣流直通；原模型與原印件不改寫。

## 選定模型與管長結論

接頭選總高 **{sel['adapter_height_mm']:g} mm**、三個外徑 **50 mm**／內徑 **46 mm**套管端、插入長25 mm；保留82×88 mm入口與118×120×3 mm原12孔法蘭。三路共用口徑，未加入中央塞塊。吹嘴淨長150 mm、縫寬16 mm，內部展寬段{sel['nozzle_length_mm']:g} mm；選型細節見`final_selection.json`及`nozzle_shape_screening.json`。

下表全部以**假設入口總表壓400 Pa**、空氣密度1.2 kg/m³、三個相同吹嘴計算，並非已量到的鼓風機實際風量。50／70代表中管裁切50 cm、左右各70 cm；已扣兩端各25 mm套入，等效51 mm通道長為45／65 cm。其他組同樣扣除，勿再重複加算接管段。

| 中管／側管裁切長cm | 左路m³/min | 中路m³/min | 右路m³/min | 合計m³/min | 相對三路平均最大偏差 | 出口面積換算平均風速m/s |
|---|---:|---:|---:|---:|---:|---:|
{table}

在此模型中，50／70 cm與60／80 cm相對100／120 cm總流量分別增加 **{improvement50:.2f}%、{improvement60:.2f}%**；前兩者相差 **{difference:.2f}%**。管長比較固定其他阻力假設；若短管必須急彎或壓扁，實際排序可能不同。小幅差異不能視為實測保證。

![模型外觀](images/Design_overview.png)
![單台風機組裝示意](images/Assembly_schematic.png)
![管長比較](images/CFD_pipe_length_comparison.png)

## 吹嘴與出口分布

末端前8 mm保持直線縫，沒有中央核心、外部長補強肋或90°流道。出風分布以X=0、Y=±70 mm的140 mm中心線衡量；同面積動壓指標為固定140×20 mm範圍平均`0.5ρ max(Uz,0)²`；動量通量為固定140×80 mm範圍積分`ρ max(Uz,0)² dA`。它們是自由射流比較指標，不是傘面實際受力、剪力或乾燥時間。

本次選定吹嘴{target_text}中心線變異係數10%的設計目標；實際值如下。每組出口外流場以該組較弱支路的流量計算，不把中心較強支路當成全部三路。

| 管長組cm | 距出口cm | 140mm中心線平均Uz m/s | 中心線CV | 同面積動壓指標Pa | 同範圍動量通量N |
|---|---:|---:|---:|---:|---:|
{jettable}

![出口分布](images/CFD_outlet_profiles.png)
![距出口8cm的速度圖](images/CFD_80mm_velocity_maps.png)
![接頭實際求解剖面](images/CFD_adapter_flow_section.png)

本次增加三個吹嘴與長軟管，覆蓋面積與原216×16 mm單嘴不同；不把總流量增加直接稱為局部吹力更強。

## ANSYS方法與限制

Fluent Student 2026 R1、3D雙精度、4 CPU、定常不可壓縮SST k–ω，ρ=1.2 kg/m³、μ=1.8×10⁻⁵ Pa·s。入口採均勻速度或均勻總壓、湍流強度5%，吹嘴入口水力直徑46 mm、接頭入口84 mm；外部環境為0 Pa壓力開放邊界。模型包含三路接頭與吹嘴；波紋軟管以等效阻力表示，未逐一建立波紋幾何。基準Darcy摩擦因子0.04、每路彎曲損失係數0.5，接合步差損失係數合計0.15；均為假設，非此軟管的量測數據，敏感度範圍也不是實品的保證上下限。

先由兩個處方流量的吹嘴CFD取得流量—所需總壓曲線，再與軟管阻力一起作為三個出口的等效負載；另在最終三個工作流量檢查開放外流場所需總壓，不以兩點擬合殘差作為精度證明。計算包含出口動能修正，並以接頭出口質量加權總壓核對一維阻力目標，誤差須小於2%。本次使用的[Fluent porous-jump模型](https://ansyshelp.ansys.com/public/Views/Secured/corp/v252/en/flu_ug/flu_ug_bcs_sec_bound_cond.html)只代表未展開的管路／吹嘴阻力，並非列印件內的實體濾網。

200／400 Pa壓力、摩擦因子與彎曲程度比較見`CFD_summary.csv`。風機未提供完整P–Q曲線；11 m³/min與460 Pa靜壓不能直接指定為本整套的共同工作點。模型不含葉輪、蝸殼、實際入口旋流、列印粗糙度、漏氣、傘布遮擋、液膜、液滴或蒸發，因此不能判定實機風機失速、吸入口回流或10秒吹乾已被解決。

接頭逆流統計只含實體接頭內、沿局部流向速度低於−0.01 m/s的單元體積；外部噴流邊界吸入環境空氣不視為鼓風機回流。

標準與較細O形網格的接頭總流量差為 **{fine_adapter['total_flow_change_pct']:+.2f}%**，最大支路佔比差 **{fine_adapter['maximum_share_change_percentage_points']:.3f}個百分點**。這是聯合網格密度／拓樸檢查，未做三層GCI。吹嘴另做截面加密與計算區域延伸，結果在`mesh_sensitivity_checks.json`；不能把這些差值當作物理誤差信賴區間。各網格cells與nodes均小於Student的一百萬限制，原生Fluent檢查確認正體積。

工程收斂門檻：連續性殘差<10⁻⁴，速度<10⁻⁶，k與ω<10⁻⁵；最後兩批流量及入口壓力變化<0.5%，質量不平衡<0.1%。另列是否全部殘差<10⁻⁵。

| 案例 | 最後迭代 | 連續性殘差 | 質量不平衡% | 工程收斂 | 全殘差<10⁻⁵ |
|---|---:|---:|---:|---|---|
{convtable}

原生case/data已重新開啟核對壓力及流量，見`native_reopen_checks.json`。完整原始CFD保留於計算目錄`{ROOT}`的`cfd`，ZIP收錄輕量結果與驗證紀錄。此Windows Fluent環境的重算須使用英文路徑；中文交付資料夾可用於列印及Blender，勿直接在中文路徑啟動CFD腳本。

## 列印與組裝

單位mm、100%匯入。列印`print/STL/{parts['adapter']['name']}_mm.stl` **1個**與`print/STL/{parts['nozzle']['name']}_mm.stl` **3個**。可先印`fit_sample_OD50_ID46_mm.stl`試套實際51 mm軟管。管嘴沒有超過50 mm的止滑凸圈；每端套入25 mm並用管夾固定，共6處。鼓風機端沿用原固定孔及密封方式。

3MF為標準模型與擺盤，沒有經驗證的切片參數或G-code。三嘴擺盤的模型間距、5 mm brim與K1C 220×220×250 mm空間已核對。實際切片、支撐、列印剛性與公差仍需確認；支撐只可從82×88 mm入口或46 mm圓口取出，不能封住流道。切片時核對2 mm管壁與出口壁形成連續實體線。

STL獨立重讀為封閉單件、無退化面；Blender重開、61點縫寬、150 mm淨長、81個流道截面、原12孔及三個插管端尺寸皆有紀錄。這些是幾何檢查，不是實印或氣密測試。吹嘴實際固定位置須配合機構安排，本次未修改機殼。

## 實測

維持相同電壓、風機檔位、管路與含水量，在3／5／8 cm各重複3次。記錄三嘴風速、吹10秒前後重量、停風後5秒滴數、入口方向、脈動及漏氣；模板為`physical_test_template.csv`。先比較相同距離與濕布，勿把管長、出風距離與出口尺寸同時改動後只歸因於接頭。
'''
    report += '\n\n入口假設：接頭入口採均勻總壓，未重建鼓風機葉輪的旋流與偏流；各吹嘴入口採均勻軸向流，未傳遞軟管末端的偏流或旋流。因此三路均衡與長縫分布只適用於這些計算假設，實際彎管配置仍須量測。\n'
    report += '\n吹嘴細算同時加密 O-grid 並將出口後外流場由 250 mm 延長至 400 mm，屬合併敏感度比較，沒有進行三組網格的 GCI 分析。\n'
    if not fine_jet['all_5pct_targets_met']:
        report += f"\n**數值敏感度目標未完全達成。** 吹嘴所需入口總壓按流量平方正規化後，相差 {fine_jet['required_total_pressure_normalized_change_pct']:+.2f}%；保留原先 5% 目標並列為未達標。下列風速與壓力為本輪模型的條件性預測，不能宣稱網格獨立、實際風機工作點已確認，或已證明比原本列印件吹乾更快。\n"
    if not fine_converged:
        report='''**交付狀態：可列印原型。** 使用者選擇先交付原型與報告，不加做瞬態模擬。三組主要管長比較、阻力敏感度、接頭細網格已通過工程收斂；吹嘴細網格仍有殘差振盪，僅保留為診斷，沒有算作通過驗證。其網格差異與均勻度數字不可視為已確認的精度。\n\n'''+report
        report += '\nSIMPLE 延續檢查依原型交付選擇在完成前停止，未作為最終 CFD 資料；原 Coupled 細網格保存結果僅供診斷。\n'
    matrix=[
        ['原固定接口','82×88 mm 入口；118×120×3 mm 法蘭；原12孔','CAD重讀通過','原檔27份雜湊未變'],
        ['三路插管端','外徑50／內徑46 mm；插入25 mm','CAD量測通過','適配內徑51 mm軟管；實物鬆緊待試配'],
        ['吹嘴出口','150×16 mm；總高188 mm；無中央核心','61點淨縫量測通過','兩端設計高度一致'],
        ['主要三組管長','中／側50／70、60／80、100／120 cm','工程收斂通過','400 Pa總壓及假設管阻；實際風機工作點未確認'],
        ['三路均衡','基準偏差≤5%；敏感度≤10%','本輪假設下通過','實際彎管與軟管阻力仍須量測'],
        ['接頭網格敏感度','總流量差<3%；分流占比差<1百分點','通過','加密後總流量差約0.065%'],
        ['吹嘴細網格','工程收斂與5%敏感度目標','通過' if fine_converged and fine_jet['all_5pct_targets_met'] else '未完成驗證，僅診斷','精度與均勻度不可視為已確認'],
        ['K1C列印','220×220×250 mm，含5 mm brim空間','幾何排版通過','3MF為通用幾何；未切片、未實印'],
        ['吹乾效果提升','與目前列印件比較','未證實','需同風機條件、距離與濕傘實測']]
    with (ROOT/'verification_matrix.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['功能或檢查','規格或目標','狀態','限制或備註']);w.writerows(matrix)
    report += '\n[功能與驗證表](verification_matrix.csv) 彙整了已通過、未通過及尚未實測的項目。\n'
    report += '\n部分殘差振盪的案例使用 Coupled 全域偽時間續算，將時間縮放係數降至 0.1，協助穩態迭代收斂；氣流模型、二階離散、負載邊界及收斂門檻保持一致。做法參考 [Fluent 偽時間法官方說明](https://ansyshelp.ansys.com/public/Views/Secured/corp/v252/en/flu_ug/flu_ug_sec_solve_pseudo.html)，各案例實際設定與負載前後對照見 continuation_boundary_integrity.json。\n'
    if sel.get('fine_nozzle_numerical_method','').startswith('SIMPLE'):
        report += '\n細網格吹嘴另從已保存的 Coupled 解進行 SIMPLE 數值延續，仍使用相同 SST 模型、實體邊界與二階離散。原 Coupled 細網格解保留在計算資料夾，最終採用通過工程收斂與原生檔重讀的延續解；這項合併敏感度比較也包含求解演算法的差異。\n'
    report += '\n組裝時從每個圓管端面量 25 mm 畫記號，讓軟管按記號插入後以管夾固定；管長模型以這個插入深度計算。接頭採外徑 50 mm 光面插管端，沒有使用原版外徑 51.2 mm 的凸環。\n'
    reverse_rows=[]
    for case in list(sel['pipe_cases'].values())+[sel['fine_adapter_case']]:
        r=read(ROOT/'cfd'/case/'results.json')
        reverse_rows.append(dict(case=case,component='splitter',reverse_volume_pct=r['internal_negative_local_flow_volume_pct'],
            required_inlet_total_pressure_Pa=r['reports']['ptin'],component_total_pressure_loss_Pa=r['adapter_total_pressure_loss_Pa']))
    for case in list(sel['jet_cases'].values())+[sel['fine_jet_case']]:
        r=read(ROOT/'cfd'/case/'results.json')
        with np.load(ROOT/'cfd'/case/'cell_fields.npz') as cells:
            z=cells['SV_CENTROID'].reshape(-1,3)[:,2];inside=(z>=0)&(z<r['conditions']['height_mm']/1000)
            reverse=inside&(cells['SV_W']<-.01);fraction=100*float(cells['SV_VOLUME'][reverse].sum()/cells['SV_VOLUME'][inside].sum())
        body_metrics=jet_metrics(case)
        reverse_rows.append(dict(case=case,component='nozzle',reverse_volume_pct=fraction,required_inlet_total_pressure_Pa=r['reports']['ptin'],component_total_pressure_loss_Pa=body_metrics['nozzle_body_total_pressure_loss_Pa']))
    with (ROOT/'internal_recirculation.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(reverse_rows[0]));w.writeheader();w.writerows(reverse_rows)
    reverse_table='\n'.join(f"| {r['case']} | {r['component']} | {r['reverse_volume_pct']:.4f}% | {r['required_inlet_total_pressure_Pa']:.2f} | {r['component_total_pressure_loss_Pa']:.2f} |" for r in reverse_rows)
    report += '\n\n內部迴流統計只計實體流道，排除外部捲吸及虛擬負載管段。接頭按局部流向、吹嘴按 Z 流向，統計速度低於 −0.01 m/s 的區域體積比。這是反向速度區的體積比例，不能當作倒灌流量或實際風機失速判定。吹嘴本體壓損由入口總壓減去出口後 0.01 mm 淨縫截面的向外質量流率加權總壓，沒有將遠端外流域混合損失列入。\n\n| 案例 | 部件 | 內部反向區體積比 | 入口總壓 Pa | 本體總壓損 Pa |\n|---|---|---:|---:|---:|\n'+reverse_table+'\n'
    report += '\n![固定法蘭、出口淨縫與高度尺寸核對](images/CAD_dimension_checks.png)\n'
    (ROOT/'README_三路接頭與150x16mm吹嘴.md').write_text(report,encoding='utf-8')
    with (ROOT/'physical_test_template.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['pipe_configuration','distance_mm','repeat','supply_V','fan_setting','left_speed_m_s','center_speed_m_s','right_speed_m_s','wet_mass_before_g','mass_after_10s_g','drops_in_5s_after_stop','inlet_direction','pulsation','notes'])
        for key in ['50_70','60_80','100_120']:
            for d in [30,50,80]:
                for rep in [1,2,3]:w.writerow([key,d,rep]+['']*11)
    with (ROOT/'hardware.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['item','quantity','note']);w.writerows([['printed splitter',1,parts['adapter']['name']],['printed nozzle',3,parts['nozzle']['name']],['hose clamps',6,'51 mm hose'],['original flange screws','reuse','original 12 positions']])
    (ROOT/'requirements.txt').write_text(subprocess.run([sys.executable,'-m','pip','freeze'],capture_output=True,text=True,check=True).stdout,encoding='utf-8')
    # Export a compact audit table without claiming all discarded cases passed.
    cfdrows=[]
    for name in report_cases:
        r=read(ROOT/'cfd'/name/'results.json');c=r['conditions'];is_adapter='branch_flow_m3_min' in r
        cfdrows.append(dict(case=name,kind='adapter_and_network' if is_adapter else 'nozzle',converged=cv[name]['engineering_convergence_pass'],mass_imbalance_pct=r['mass_imbalance_pct'],
            prescribed_inlet_total_pressure_Pa=c.get('pressure',400) if is_adapter else c.get('hypothetical_inlet_total_pressure_Pa'),computed_inlet_total_pressure_Pa=r['reports']['ptin'],
            Darcy_friction_factor=c.get('friction',.04) if is_adapter else None,bend_loss_coefficient=c.get('bend',.5) if is_adapter else None,
            effective_center_pipe_m=c.get('center') if is_adapter else None,effective_side_pipe_m=c.get('side') if is_adapter else None,
            total_flow_m3_min=r.get('total_flow_m3_min',r.get('nozzle_flow_m3_min')),balance_error_pct=r.get('balance_error_pct'),adapter_loss_Pa=r.get('adapter_total_pressure_loss_Pa')))
    with (ROOT/'CFD_summary.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(cfdrows[0]));w.writeheader();w.writerows(cfdrows)
    paths=[ROOT/n for n in ['README_三路接頭與150x16mm吹嘴.md','DATA_STATUS.md','final_selection.json','requirements_and_constraints.json','design_acceptance.json','source_integrity.json','native_reopen_checks.json','mesh_sensitivity_checks.json','external_curve_consistency.json','pipe_length_comparison.csv','internal_recirculation.csv','CFD_summary.csv','verification_matrix.csv','physical_test_template.csv','hardware.csv','requirements.txt','nozzle_shape_screening.json','selected_shape_work.json','nozzle_pressure_curves.json']]
    paths+=list((ROOT/'images').glob('*.png'))+list((ROOT/'cad').glob('*.json'))+[ROOT/'cad/ThreeWay150_51mm_System.blend']+list((ROOT/'print').glob('*.json'))
    for part in geo['parts']:paths+=[ROOT/'print/STL'/(part['name']+'_mm.stl'),ROOT/'print/3MF'/(part['name']+'.3mf'),ROOT/'cad/reference'/(part['name']+'.stl')]
    paths.append(ROOT/'print/3MF/nozzles_quantity3_K1C.3mf')
    for name in report_cases:
        paths += [ROOT/'cfd'/name/f for f in ['results.json','history.json','mesh_summary.json','convergence.json']]
        paths += list((ROOT/'cfd'/name).glob('profile_*.csv'))
        if (ROOT/'cfd'/name/'performance_metrics.json').exists():paths.append(ROOT/'cfd'/name/'performance_metrics.json')
        if (ROOT/'cfd'/name/'boundary_conditions.json').exists():paths.append(ROOT/'cfd'/name/'boundary_conditions.json')
        if (ROOT/'cfd'/name/'continuation_boundary_integrity.json').exists():paths.append(ROOT/'cfd'/name/'continuation_boundary_integrity.json')
        if (ROOT/'cfd'/name/'iteration_control_adjustment.json').exists():paths.append(ROOT/'cfd'/name/'iteration_control_adjustment.json')
        if (ROOT/'cfd'/name/'linear_solver_adjustment.json').exists():paths.append(ROOT/'cfd'/name/'linear_solver_adjustment.json')
        if (ROOT/'cfd'/name/'high_order_iteration_adjustment.json').exists():paths.append(ROOT/'cfd'/name/'high_order_iteration_adjustment.json')
        for evidence in ['solver_method_adjustment.json','initial_state_provenance.json']:
            if (ROOT/'cfd'/name/evidence).exists():paths.append(ROOT/'cfd'/name/evidence)
    active_sources=['geometry.py','meshlib.py','ogrid_nozzle_mesh.py','build_adapter_mesh.py','legacy_study.py','network.py','adapter_study.py','run_solver.py','resume_nozzle.py','analyze.py','cad_utils.py','build_cad.py','render_cad.py','verify_print.py','verify_native_blend.py','convergence_control.py','run_logged.py','auto_design.py','finalize_delivery.py','dimension_drawing.py','reference_splitter_spec.json']
    paths += [ROOT/n for n in active_sources];paths=sorted(set(paths));assert all(p.exists() for p in paths)
    paths += [ROOT/n for n in ['resume_adapter.py','tune_active_nozzle.py','tighten_fine_linear_solver.py','relax_fine_high_order.py','continue_nozzle_segregated.py','finish_cfd.py','verify_native_prototype.py']];paths=sorted(set(paths))
    manifest={p.relative_to(ROOT).as_posix():digest(p) for p in paths};(ROOT/'MANIFEST.sha256').write_text('\n'.join(f'{v}  {k}' for k,v in manifest.items())+'\n',encoding='utf-8')
    pack=ROOT/'ThreeWay_51mm_150x16_PrintPack.zip'
    with zipfile.ZipFile(pack,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in paths+[ROOT/'MANIFEST.sha256']:z.write(p,p.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(pack) as z:
        assert z.testzip() is None
        for n,d in manifest.items():assert hashlib.sha256(z.read(n)).hexdigest()==d
    write(ROOT/'package_checks.json',dict(zip=pack.name,member_count=len(manifest)+1,bytes=pack.stat().st_size,CRC_and_member_hashes_pass=True,credentials_and_raw_CFD_excluded=True))
    print('PRINT_PACKAGE_READY',str(pack),flush=True)

if __name__=='__main__':main()
