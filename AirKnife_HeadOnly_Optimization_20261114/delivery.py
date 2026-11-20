"""Auditable report, plots and print package from finished native solutions."""
import csv,hashlib,json,shutil,zipfile,subprocess,sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image,ImageDraw,ImageFont
from scipy.interpolate import LinearNDInterpolator
from geometry import ROOT,DESIGNS,activate,section
from analyze import main as analyze,read

def save(path,value):
    (ROOT/path).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')

def metrics(name):
    return read(ROOT/('references/'+name if name in ['ref216','ref252'] else 'cfd/'+name)/'performance_metrics.json')

def pct(a,b):return 100*(a/b-1)

def plots(selection):
    names=['ref216']+[selection['standard_cases'][n] for n in selection['delivered_designs']]
    labels=['Printed baseline 216 x 16 / H260']+[selection['labels'][n] for n in selection['delivered_designs']]
    fig,axes=plt.subplots(1,3,figsize=(14,4.8),layout='constrained')
    for name,label in zip(names,labels):
        p=ROOT/('references/'+name if name=='ref216' else 'cfd/'+name)
        for d,ax in zip([30,50,80],axes):
            values=np.loadtxt(p/f'profile_{d}mm.csv',delimiter=',',skiprows=1)
            ax.plot(values[:,0],values[:,1],label=label,lw=1.8)
            ax.set(xlabel='Y across outlet (mm)',ylabel='Normal velocity at X=0 (m/s)',title=f'{d} mm after outlet',xlim=(-110,110))
            ax.grid(alpha=.2)
    axes[1].legend(fontsize=8,loc='lower center');fig.suptitle('Fluent SST: hypothetical inlet TOTAL pressure 400 Pa; smooth walls; no fabric')
    fig.savefig(ROOT/'images/CFD_profiles.png',dpi=180);plt.close(fig)
    fine_designs=['ref216']+[n for n in selection['delivered_designs'] if n in selection['fine_cases']]
    fine_names=[selection['fine_cases'][n] for n in fine_designs]
    fine_labels=[labels[(['ref216']+selection['delivered_designs']).index(n)] for n in fine_designs]
    fig,axes=plt.subplots(1,2,figsize=(11,4.8),layout='constrained')
    for name,label in zip(fine_names,fine_labels):
        m=metrics(name);distance=[30,50,80]
        axes[0].plot(distance,[m[f'{d}mm']['same_200x16_patch_normal_dynamic_pressure_mean_Pa'] for d in distance],'o-',label=label)
        axes[1].plot(distance,[m[f'{d}mm']['same_200x80_strip_forward_momentum_N'] for d in distance],'o-',label=label)
    axes[0].set(ylabel='Mean normal dynamic-pressure proxy (Pa)',title='Fixed 200 x 16 mm patch')
    axes[1].set(ylabel='Forward momentum flux (N)',title='Fixed 200 x 80 mm strip')
    for ax in axes:ax.set(xlabel='Distance after outlet (mm)',xticks=[30,50,80]);ax.grid(alpha=.2)
    axes[0].legend(fontsize=8);fig.suptitle('Fine mesh comparison at 400 Pa TOTAL: free-jet proxies, not measured drying force')
    fig.savefig(ROOT/'images/CFD_same_area_fine.png',dpi=180);plt.close(fig)
    fig,axes=plt.subplots(1,len(fine_names),figsize=(5*len(fine_names),6.5),layout='constrained',squeeze=False)
    for ax,case,design,label in zip(axes[0],fine_names,fine_designs,fine_labels):
        activate(design);c=DESIGNS[design];height=c['height'];data=np.load(ROOT/'cfd'/case/'short_cut_fields.npz')
        xy=np.c_[data['centroids'][:,0]*1000,data['centroids'][:,2]*1000-height]
        xx=np.linspace(-35,35,151);zz=np.linspace(-70,100,241);xg,zg=np.meshgrid(xx,zz)
        f=LinearNDInterpolator(xy,np.c_[data['x-velocity'],data['z-velocity']]);v=f(np.c_[xg.ravel(),zg.ravel()]).reshape(*xg.shape,2)
        d=np.array([section(min(z+height,height))[1] for z in zz]);solid=(zg<0)&(np.abs(xg)>d[:,None]/2)
        v[solid]=np.nan
        plot=ax.contourf(xx,zz,v[:,:,1],levels=np.linspace(-2,28,31),cmap='turbo',extend='both')
        ax.streamplot(xx,zz,v[:,:,0],v[:,:,1],color='white',density=.8,linewidth=.45,arrowsize=.6)
        internal=zz<=0;ax.plot(d[internal]/2,zz[internal],color='black',lw=1);ax.plot(-d[internal]/2,zz[internal],color='black',lw=1)
        ax.axhline(0,color='black',lw=.6,ls='--');ax.set(xlabel='X (mm)',ylabel='Z relative to outlet (mm)',title=label,aspect='equal')
    fig.colorbar(plot,ax=list(axes[0]),label='Normal velocity Uz (m/s)',shrink=.8)
    fig.suptitle('Actual Fluent fine solutions: short-direction section at Y=1 mm; 400 Pa TOTAL')
    fig.savefig(ROOT/'images/CFD_flow_sections.png',dpi=180);plt.close(fig)
    # Dimensioned orthogonal section is generated directly from the CAD profile.
    fig,axes=plt.subplots(1,len(selection['delivered_designs']),figsize=(12,5),layout='constrained',squeeze=False)
    for ax,name in zip(axes[0],selection['delivered_designs']):
        activate(name);c=DESIGNS[name];z=np.linspace(194,c['height'],301);depth=np.array([section(max(v,200))[1] for v in z])
        ax.plot(-depth/2,z,color='#116c77');ax.plot(depth/2,z,color='#116c77')
        ax.fill_betweenx(z,-depth/2,depth/2,color='#cdebf0',alpha=.5)
        ax.axhline(200,color='gray',ls='--',lw=1);ax.annotate('Body unchanged / Z200',xy=(10,200),xytext=(19,199),fontsize=9)
        ax.annotate('',xy=(-8,c['height']+2),xytext=(8,c['height']+2),arrowprops=dict(arrowstyle='<->'))
        ax.text(0,c['height']+4,'16 mm clear gap',ha='center',fontsize=10)
        ax.set(title=selection['labels'][name],xlabel='X (mm)',ylabel='Z from original flange (mm)',xlim=(-35,65),ylim=(190,c['height']+13),aspect='equal')
        ax.text(19,210,f"Clear span: {c['span']} mm\nFlow length: {c['height']-200} mm\nPrinted height: {c['height']-194} mm\nLast 6 mm straight\nNo central core / ribs",fontsize=9)
    fig.suptitle('Inner flow section at Y=0; installation interface remains at Z200')
    fig.savefig(ROOT/'images/CAD_dimensioned_sections.png',dpi=180);plt.close(fig)
    font=ImageFont.truetype('C:/Windows/Fonts/msjh.ttc',34);small=ImageFont.truetype('C:/Windows/Fonts/msjh.ttc',25)
    image=Image.new('RGB',(1600,1070),'#f1f4f6');draw=ImageDraw.Draw(image)
    draw.text((35,20),'只換上方吹嘴｜原本200 mm本體保留',font=font,fill='#18313e')
    for j,name in enumerate(selection['delivered_designs']):
        c=DESIGNS[name];photo=Image.open(ROOT/'images'/f'CAD_{name}_assembly.png').convert('RGB');photo.thumbnail((760,770))
        x=j*800+20;image.paste(photo,(x,90));draw.text((x+15,870),selection['labels_zh'][name],font=font,fill='#18313e')
        draw.text((x+15,925),f"出口 {c['span']}×16 mm｜整組 {c['height']} mm",font=small,fill='#18313e')
        draw.text((x+15,965),'4顆M3螺絲接回原本體；無補強肋、無核心',font=small,fill='#18313e')
    image.save(ROOT/'images/Design_comparison.png')

def main():
    analyze();selection=read(ROOT/'selection.json');geo=read(ROOT/'cad/geometry_checks.json');designs=selection['delivered_designs']
    assert set(designs)==set(geo['designs'])
    conv={p.parent.name:read(p) for p in sorted((ROOT/'cfd').glob('*/convergence.json'))}
    assert all(v['engineering_convergence_pass'] for v in conv.values()),[(k,v) for k,v in conv.items() if not v['engineering_convergence_pass']]
    save('cfd/convergence_summary.json',conv)
    sensitivities={};fine_ref=metrics(selection['fine_cases']['ref216'])
    for design in ['ref216']+[n for n in designs if n in selection['fine_cases']]:
        standard='ref216' if design=='ref216' else selection['standard_cases'][design]
        fine=selection['fine_cases'][design];a=metrics(standard);b=metrics(fine)
        fields={'Q_m3_min':(a['computed_Q_m3_min'],b['computed_Q_m3_min']),
            'slot_Uz_m_s':(a['slot_mean_Uz_m_s'],b['slot_mean_Uz_m_s'])}
        for d in [30,50,80]:
            for key in ['same_200x16_patch_normal_dynamic_pressure_mean_Pa','same_200x80_strip_forward_momentum_N']:
                fields[f'{d}mm_'+key]=(a[f'{d}mm'][key],b[f'{d}mm'][key])
        sensitivities[design]={k:dict(standard=x,fine=y,change_pct=pct(y,x)) for k,(x,y) in fields.items()}
    save('cfd/mesh_and_domain_sensitivity.json',{'method':'Combined finer cross section, 1 mm axial head mesh and downstream reach 250 to 400 mm; not GCI or a confidence interval','cases':sensitivities})
    gains={}
    for name in designs:
        if name not in selection['fine_cases']:continue
        m=metrics(selection['fine_cases'][name]);gains[name]={}
        for d in [30,50,80]:
            gains[name][f'{d}mm']={k:pct(m[f'{d}mm'][k],fine_ref[f'{d}mm'][k]) for k in ['same_200x16_patch_normal_dynamic_pressure_mean_Pa','same_200x80_strip_forward_momentum_N','common_200mm_line_mean_Uz_m_s']}
    save('cfd/fine_same_area_gains_pct.json',gains)
    rows=[]
    for p in sorted((ROOT/'cfd').glob('*/results.json')):
        r=read(p);c=r['conditions'];mesh=read(p.parent/'mesh_summary.json');cells=np.load(p.parent/'cell_fields.npz');xyz=cells['SV_CENTROID'].reshape(-1,3)
        internal=xyz[:,2]<c['height_mm']/1000;negative=internal&(cells['SV_W']<-.01)
        area=100*float(cells['SV_VOLUME'][negative].sum()/cells['SV_VOLUME'][internal].sum())
        m=metrics(p.parent.name) if c['external_free_jet'] else None
        row={'case':p.parent.name,'span_mm':c['span_mm'],'gap_mm':c['gap_mm'],'total_height_mm':c['height_mm'],'cells':mesh['cells'],'nodes':mesh['nodes'],
            'fixed_total_pressure_Pa':c['hypothetical_inlet_total_pressure_Pa'],'fixed_flow_m3_min':c['prescribed_Q_m3_min'],
            'Q_m3_min':r['nozzle_flow_m3_min'],'nozzle_total_pressure_loss_Pa':m['nozzle_total_pressure_loss_Pa'] if m else r['pressure_loss_to_domain_outlet_Pa'],
            'internal_negative_Uz_volume_pct':area,'minimum_internal_Uz_m_s':float(cells['SV_W'][internal].min()),
            'mass_imbalance_pct':r['mass_imbalance_pct'],'engineering_convergence_pass':conv[p.parent.name]['engineering_convergence_pass']}
        for d in [30,50,80]:
            for key in ['same_200x16_patch_normal_dynamic_pressure_mean_Pa','same_200x80_strip_forward_momentum_N','covered_line_CV_pct']:
                row[f'{d}mm_'+key]=m[f'{d}mm'][key] if m else None
        rows.append(row)
    with (ROOT/'CFD_comparison.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    start=read(ROOT/'original_sources.json');source=ROOT.parent/start['source']
    hashes={k:hashlib.sha256((source/k).read_bytes()).hexdigest() for k in start['files']};assert hashes==start['files']
    body_paths=['cad/reference/body_onepiece.stl','print/STL/body_onepiece_mm.stl']
    assert all(hashlib.sha256((source/p).read_bytes()).hexdigest()==hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in body_paths)
    save('source_integrity.json',{'originals_unchanged':True,'file_count':len(hashes),'body_copies_byte_identical':True,'files':hashes})
    plots(selection)
    (ROOT/'requirements.txt').write_text(subprocess.run([sys.executable,'-m','pip','freeze'],capture_output=True,text=True,check=True).stdout,encoding='utf-8')
    parts={r['group']:r for r in geo['parts']};q3base=read(ROOT.parent/'AirKnife_16mm_Wider_ANSYS_20261114/cfd/body_H260_W216/results.json')
    geometry_table='\n'.join(f"| {selection['labels_zh'][n]} | {DESIGNS[n]['span']}×16 | {parts[n]['maximum_outside_width_mm']:.1f} | {DESIGNS[n]['height']} | {DESIGNS[n]['height']-194} | {parts[n]['print_size_mm'][0]:.1f}×{parts[n]['print_size_mm'][1]:.1f}×{parts[n]['print_size_mm'][2]:.0f} |" for n in designs)
    metric_table=''
    for label,name in [('原版216×16/H260',selection['fine_cases']['ref216'])]+[(selection['labels_zh'][n],selection['fine_cases'][n]) for n in designs if n in selection['fine_cases']]:
        m=metrics(name);v=m['80mm'];metric_table+=f"| {label} | {m['computed_Q_m3_min']:.3f} | {m['slot_mean_Uz_m_s']:.2f} | {v['same_200x16_patch_normal_dynamic_pressure_mean_Pa']:.2f} | {v['same_200x80_strip_forward_momentum_N']:.4f} | {v['common_200mm_line_mean_Uz_m_s']:.2f} |\n"
    gains_table='\n'.join(f"| {selection['labels_zh'][n]} | {d/10:g} | {gains[n][f'{d}mm']['same_200x16_patch_normal_dynamic_pressure_mean_Pa']:+.2f}% | {gains[n][f'{d}mm']['same_200x80_strip_forward_momentum_N']:+.2f}% |" for n in gains for d in [30,50,80])
    standard_base=metrics('ref216');standard_table=''
    for label,name in [('原版216×16/H260','ref216')]+[(selection['labels_zh'][n],selection['standard_cases'][n]) for n in designs]:
        m=metrics(name);v=m['80mm']
        standard_table+=f"| {label} | {m['computed_Q_m3_min']:.3f} | {v['same_200x16_patch_normal_dynamic_pressure_mean_Pa']:.2f} | {pct(v['same_200x16_patch_normal_dynamic_pressure_mean_Pa'],standard_base['80mm']['same_200x16_patch_normal_dynamic_pressure_mean_Pa']):+.2f}% | {v['same_200x80_strip_forward_momentum_N']:.4f} |\n"
    q3_table=f"| 原版216×16/H260 | {q3base['pressure_loss_to_domain_outlet_Pa']:.3f} | — |\n"
    for n in designs:
        r=read(ROOT/'cfd'/('screen_'+n)/'results.json');loss=r['pressure_loss_to_domain_outlet_Pa']
        q3_table+=f"| {selection['labels_zh'][n]} | {loss:.3f} | {pct(loss,q3base['pressure_loss_to_domain_outlet_Pa']):+.2f}% |\n"
    conv_table='\n'.join(f"| {k} | {v['last_iteration']} | {v['last_residuals']['continuity']:.2g} | {v['mass_imbalance_pct']:.3g} | {'是' if v['all_residuals_under_1e_minus_5'] else '否'} |" for k,v in conv.items())
    sens_table='\n'.join(f"| {selection['labels_zh'].get(n,'原版216×16/H260')} | {v['Q_m3_min']['change_pct']:+.2f}% | {v['80mm_same_200x16_patch_normal_dynamic_pressure_mean_Pa']['change_pct']:+.2f}% | {v['80mm_same_200x80_strip_forward_momentum_N']['change_pct']:+.2f}% |" for n,v in sensitivities.items())
    text=f'''# 保留現有本體：16 mm吹嘴改良與ANSYS比較

2026-11-14。實際基準為你已列印的 **216×16 mm、整組260 mm、無補強肋版**。本次只重印上方吹嘴，保留原200 mm本體、原鼓風機法蘭12孔，以及4個M3接合點。原始版本的檔案雜湊全數未變。

## 使用選擇

{selection['recommendation_zh']}

| 版本 | 出口淨尺寸mm | 最大外寬mm | 整組總高mm | 吹嘴實體高mm | STL已轉45°的列印尺寸mm |
|---|---:|---:|---:|---:|---:|
{geometry_table}

兩款都沒有中央核心、外部長補強肋及定位銷。空氣維持直通，出口方向與原16 mm無肋版一致。主壁厚3 mm，最後6 mm以外側斜面漸薄至1.6 mm，末端1 mm保持1.6 mm；內側出口最後6 mm為16 mm直段。壁厚與較短零件是幾何設計選擇，尚未驗證實際抗翹曲、剛性或列印結果。

![本體與吹嘴](images/Design_comparison.png)
![剖面尺寸](images/CAD_dimensioned_sections.png)

## 公平比較：同一範圍、同一假設壓力

比較的是原版的理想CAD與新版CAD，尚未量測你手上實體件的翹曲、密封或真實出口尺寸。自由射流算例固定入口**總表壓400 Pa**，外界靜表壓0 Pa；此條件用來比較幾何，不代表鼓風機的實際工作點。你提供的11 m³/min與460 Pa靜壓不能直接同時當成此吹嘴的工作流量及入口總壓；缺少完整風機P–Q曲線、入口旋流和實測壓力。

以下全部為加密網格互相比較。距出口8 cm，固定中央 **200×16 mm**面積平均`0.5ρ max(Uz,0)²`；另外在固定 **200×80 mm**範圍積分`ρ max(Uz,0)² dA`。這兩者是自由射流的動壓及動量通量指標，並非傘面實際壓力、剪力、吹水量或乾燥時間。中心線速度取X=0、Y=±100 mm。

| 版本 | 預測流量m³/min | 出口平均Uz m/s | 同面積動壓指標Pa | 同範圍動量通量N | 中心線平均Uz m/s |
|---|---:|---:|---:|---:|---:|
{metric_table}

| 版本 | 出口距離cm | 同面積動壓相對原版 | 同範圍動量相對原版 |
|---|---:|---:|---:|
{gains_table}

228 mm加寬款只完成標準網格篩選，與原版標準網格互相比較如下，不與加密結果混用：

| 版本 | 流量m³/min | 8cm同面積動壓Pa | 同面積動壓相對原版 | 同範圍動量N |
|---|---:|---:|---:|---:|
{standard_table}

**降低內部壓損的百分比，不能當作吹力增加的百分比。** 原版在此假設壓力下已經有較高中心線速度，因此只換上段、維持16 mm縫寬時，改善空間有限。不能據此承諾實際吹力明顯變強或10秒吹乾。

![相同範圍比較](images/CFD_same_area_fine.png)
![3、5、8cm分布](images/CFD_profiles.png)
![實際求解流場剖面](images/CFD_flow_sections.png)

## 固定流量壓損與回流

另以3 m³/min入口體積流量、出口靜表壓0 Pa做內部流道比較。入口至出口總壓差如下。

| 版本 | 總壓損Pa | 相對原版 |
|---|---:|---:|
{q3_table}

內部反向流動採`Z<出口高度`且`Uz<−0.01 m/s`的單元體積，詳見`CFD_comparison.csv`。外界邊界的逆流代表射流吸入環境空氣，不能直接視為鼓風機吸入口回流。模型未包含葉輪與蝸殼，不能確認實機風機失速或吸入口回流已消除。

篩選也計算較大幅度加寬版本。快速加寬在固定流量下出現較大的局部反向流動，因此未僅依總流量較大就判定較強。所有已完成篩選數據保存在CSV及原生case/data。

## 數值驗證與適用範圍

使用本機Fluent Student 2026 R1、3D雙精度、4 CPU、定常不可壓縮空氣、SST k–ω；ρ=1.2 kg/m³、μ=1.8×10⁻⁵ Pa·s；入口湍流強度5%、水力直徑84 mm、光滑無滑移壁面。暖啟動只提供初始猜測，之後均經Fluent實際迭代。壓力、動量及湍流最後使用二階離散。

原版與216 mm短嘴做了加密截面、上段1 mm軸向網格及下游區域250→400 mm的共同檢查。228 mm加寬款的標準網格同範圍吹拂指標已較低，僅保留標準網格篩選結果，未做加密驗證。截面與區域同時改變，屬聯合敏感度檢查，未做三層GCI，也不是誤差信賴區間。每個網格均為正體積，cells及nodes各少於Student的一百萬限制。

| 版本 | 加密後流量變化 | 8cm同面積動壓變化 | 8cm同範圍動量變化 |
|---|---:|---:|---:|
{sens_table}

當增益與上述網格／計算區域變化相近時，應把差異視為不確定，不能宣稱已證實優於原版。穩態RANS的結果也未涵蓋非定常噴流、列印層紋、漏氣、軟傘面阻擋、液膜或液滴、熱傳及實際風機曲線。CFD外部模型保留出口端壁厚，外壁形狀、圓角、螺絲耳及插套沒有完整納入外部流場。

工程收斂標準：連續性殘差<10⁻⁴、速度<10⁻⁶、k和ω<10⁻⁵，最後兩批流量及入口壓力變化<0.5%，質量不平衡<0.1%。另列是否全部殘差皆<10⁻⁵，不混為同一標準。

| 案例 | 最後迭代 | 連續性殘差 | 質量不平衡% | 全殘差<10⁻⁵ |
|---|---:|---:|---:|---|
{conv_table}

原生case/data重新開啟後核對入口壓力及邊界質量流量，紀錄在`cfd/followup_reopen_checks.json`。完整網格、流場NPZ與case/data存於本資料夾`cfd`；列印ZIP只收輕量結果及檢查紀錄。

## 列印及組裝

只需印所選吹嘴的`print/STL/head_<版本>_16mm_body200_mm.stl`，單位mm、100%匯入，已在XY平面轉45°並置底。原本體不需重印。標準3MF只含模型與擺放，未含經驗證的K1C切片設定或G-code。

K1C的220×220×250 mm範圍已核對，各零件及5 mm brim均可放入。0.4 mm噴嘴、PLA/PLA+可先以0.20 mm層高、5 mm brim試切，1.6 mm出口端壁請確認至少形成4條連續實體線；薄壁區需依實際線寬與切片預覽核對。實際切片、列印、支撐需求、接縫密封及強度尚未驗證。

接口採0.25 mm名義徑向間隙，插套向下6 mm。沿用4顆M3×16螺絲和4顆M3螺帽；先放回原本體螺帽，再把吹嘴由上方插入，四顆交替鎖緊。模型已檢查插入路徑、8 mm起子空間、裝配交集、61點16 mm縫寬、出口淨長、原法蘭12孔及中央無阻擋；檢查的是CAD，不代表實體公差已合格。

## 實測紀錄

先用相同電壓、風機檔位和進風管路，在出口距傘面3、5、8 cm各測3次；每次用同一塊傘布、相同初始含水量和方向。吹10秒，量測前後重量，記錄停風後5秒滴數、吸入口方向、是否脈動及整段吹拂均勻度。若換短嘴，需重新調整整組位置以維持相同出口距離。模板為`physical_test_template.csv`。

## 方法參考

平滑收縮輪廓以五次曲線令端點斜率平順作為設計起點，並以本幾何CFD篩選；NASA風洞收縮研究不直接證明此吹嘴有效。[Bell與Mehta，NASA 1988](https://ntrs.nasa.gov/citations/19880012661)。

壓力入口採總壓、壓力出口採靜壓的設定依[Fluent邊界條件說明](https://ansyshelp.ansys.com/public/Views/Secured/corp/v252/en/flu_ug/flu_ug_bcs_sec_bound_cond.html)；實際風機工作點仍需[壓力–流量曲線](https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/discovery/UDA/user_manual/physics/fluids/topics/c_fluids_fans_specifyingcurve.html)。
'''
    (ROOT/'README_吹嘴改良與ANSYS.md').write_text(text,encoding='utf-8')
    with (ROOT/'physical_test_template.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['version','distance_mm','repeat','supply_V','fan_setting','dry_mass_g','wet_mass_before_g','mass_after_10s_g','drops_5s_after_stop','inlet_direction','pulsation','notes'])
        for name in ['printed_baseline']+designs:
            for d in [30,50,80]:
                for repeat in [1,2,3]:w.writerow([name,d,repeat]+['']*9)
    # Deliberate whitelist: no server credentials, transcripts, caches or raw CFD.
    paths=list((ROOT/'cad').glob('*.json'))+[ROOT/'cad/HeadOnly_16mm_Optimization.blend']
    paths += list((ROOT/'print').glob('*.json'))
    for part in geo['parts']:
        paths += [ROOT/'cad/reference'/(part['name']+'.stl'),ROOT/'print/STL'/(part['name']+'_mm.stl'),ROOT/'print/3MF'/(part['name']+'.3mf')]
    paths += [ROOT/'print/plates/01_body_onepiece_Z45.3mf']
    for name in designs:
        paths += [ROOT/'print/plates'/f'02_{name}_head_Z45.3mf']
        paths += [ROOT/'images'/f'CAD_{name}_{v}.png' for v in ['assembly','head']]
    paths += [ROOT/'images'/name for name in ['CFD_profiles.png','CFD_same_area_fine.png','CFD_flow_sections.png','CAD_dimensioned_sections.png','Design_comparison.png']]
    paths += [ROOT/name for name in ['README_吹嘴改良與ANSYS.md','selection.json','user_constraints.json','source_integrity.json','CFD_comparison.csv','physical_test_template.csv','requirements.txt']]
    paths += list(ROOT.glob('*.py'))
    paths += [p for p in (ROOT/'cfd').rglob('*.json') if p.name not in ['cell_fields.json']]
    paths += list((ROOT/'references').rglob('*.json'))+list((ROOT/'references').rglob('*.csv'))+list((ROOT/'cfd').glob('*/profile_*.csv'))
    paths=sorted(set(paths));manifest={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    (ROOT/'MANIFEST.sha256').write_text('\n'.join(f'{v}  {k}' for k,v in manifest.items())+'\n',encoding='utf-8')
    pack=ROOT/selection.get('printpack_name','K1C_HeadOnly_16mm_Compared_Prototypes.zip')
    with zipfile.ZipFile(pack,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for path in paths+[ROOT/'MANIFEST.sha256']:z.write(path,path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(pack) as z:
        assert z.testzip() is None
        for name,digest in manifest.items():assert hashlib.sha256(z.read(name)).hexdigest()==digest
    save('package_checks.json',{'zip':pack.name,'member_count':len(manifest)+1,'bytes':pack.stat().st_size,'CRC_and_all_member_hashes_pass':True,'raw_CFD_and_credentials_excluded':True})
    print('PACKAGE_READY',str(pack),flush=True)
    print('FINE_SAME_AREA_GAINS',json.dumps(gains),flush=True)

if __name__=='__main__':main()
