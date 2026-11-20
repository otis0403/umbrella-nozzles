"""Native technical drawings and registered CAD-render comparison; no AI images."""
from pathlib import Path
from functools import lru_cache
from PIL import Image,ImageDraw,ImageFont
import sys,math,json,hashlib
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
from geometry import section,HOLES
r=json.loads((HERE/'尺寸與方向檢查.json').read_text(encoding='utf-8'))
preview=json.loads((HERE/'預覽來源檢查.json').read_text(encoding='utf-8'))
assert preview['comparison_camera']['same_for_both_models']
assert r['coordinate_system']['inlet_global_XY_mm']==[82,88] and r['coordinate_system']['outlet_global_XY_mm']==[12,216]
FONT=Path(r'C:\Windows\Fonts\msjh.ttc')
@lru_cache(None)
def font(size):return ImageFont.truetype(str(FONT),size)
INK=(30,47,60);BLUE=(17,100,145);GRAY=(105,122,137);LIGHT=(205,217,228);ORANGE=(207,111,25)
def txt(im,xy,text,size=30,color=INK,anchor=None):ImageDraw.Draw(im).text(xy,text,font=font(size),fill=color,anchor=anchor)
def label(im,xy,text,size=29,color=BLUE):
    draw=ImageDraw.Draw(im);box=draw.textbbox(xy,text,font=font(size),anchor='mm')
    draw.rectangle((box[0]-7,box[1]-4,box[2]+7,box[3]+4),fill='white');draw.text(xy,text,font=font(size),fill=color,anchor='mm')
def dim_h(im,x1,x2,y,actual_y,text):
    d=ImageDraw.Draw(im);d.line([(x1,actual_y),(x1,y+12)],fill=GRAY,width=2);d.line([(x2,actual_y),(x2,y+12)],fill=GRAY,width=2)
    d.line([(x1,y),(x2,y)],fill=BLUE,width=3)
    d.polygon([(x1,y),(x1+12,y-5),(x1+12,y+5)],fill=BLUE);d.polygon([(x2,y),(x2-12,y-5),(x2-12,y+5)],fill=BLUE)
    label(im,((x1+x2)/2,y-25),text)
def dim_v(im,y1,y2,x,actual_x,text):
    d=ImageDraw.Draw(im);d.line([(actual_x,y1),(x-12,y1)],fill=GRAY,width=2);d.line([(actual_x,y2),(x-12,y2)],fill=GRAY,width=2)
    d.line([(x,y1),(x,y2)],fill=BLUE,width=3)
    d.polygon([(x,y1),(x-5,y1+12),(x+5,y1+12)],fill=BLUE);d.polygon([(x,y2),(x-5,y2-12),(x+5,y2-12)],fill=BLUE)
    label(im,(x+70,(y1+y2)/2),text)

# Same actual top-view renders, same pixel/mm scale, same flange overlays.
comparison=Image.new('RGB',(2400,1440),'white')
txt(comparison,(70,35),'出口方向對照｜底座與螺絲孔保持原位',58)
txt(comparison,(74,110),'同一固定法蘭、同一相機與比例；圖面橫向為 +Y，向下為 +X。',29,GRAY)
raws=['_預覽用_舊版固定法蘭俯視.png','_預覽用_新版固定法蘭俯視.png']
panel_xy=[(100,240),(1300,240)]
for index,(raw,(left,top)) in enumerate(zip(raws,panel_xy)):
    image=Image.open(HERE/raw).convert('RGB');assert image.size==(1000,1000)
    comparison.paste(image,(left,top));d=ImageDraw.Draw(comparison)
    s=1000/270;cx,cy=left+500,top+500
    # World +Y maps screen-right, world +X maps screen-down.
    flange=[cx-60*s,cy-57*s,cx+60*s,cy+61*s]
    d.rounded_rectangle(flange,radius=4*s,outline=ORANGE,width=4)
    for h in HOLES:
        px,py=cx+h['y_mm']*s,cy+h['x_mm']*s;radius=h['diameter_mm']/2*s
        d.ellipse([px-radius,py-radius,px+radius,py+radius],outline=ORANGE,width=3)
    hx,hy=cx+51*s,cy+52*s
    d.ellipse([hx-6*s,hy-6*s,hx+6*s,hy+6*s],outline=ORANGE,width=4)
    txt(comparison,(left+35,top+925),'橘色：法蘭與12孔投影（包含被外殼遮住的孔）',22,ORANGE)
    txt(comparison,(left+35,top+960),'粗圈：兩版同一角孔',22,ORANGE)
    if index==0:
        box=[cx-2*s,cy-108*s,cx+2*s,cy+108*s]
        title='舊版｜長邊沿 X，216×4 mm'
        subtitle='在這個固定法蘭方向下，長縫呈直立'
    else:
        box=[cx-108*s,cy-6*s,cx+108*s,cy+6*s]
        title='新版｜長邊沿 Y，216×12 mm'
        subtitle='長縫轉90°呈橫向，底部孔位相同'
    d.rectangle(box,outline=BLUE,width=4)
    txt(comparison,(left,175),title,37,BLUE)
    txt(comparison,(left,1280),subtitle,32,INK)
txt(comparison,(1150,665),'90°',39,BLUE)
txt(comparison,(75,1370),'氣流仍沿 +Z 直通；90°指長縫朝向。橘色與藍色線為按 CAD 尺寸疊加的標示。',28,GRAY)
comparison.save(HERE/'03_固定法蘭_新舊出口方向對照.png',dpi=(200,200))

# Dimension drawing: YZ front, XZ side, and fixed-flange XY overlay.
im=Image.new('RGB',(2800,1800),'white');d=ImageDraw.Draw(im)
txt(im,(70,40),'200 mm 單件吹嘴｜216×12 mm 橫向出口',62)
txt(im,(75,125),'入口 X×Y＝82×88 mm；出口 X×Y＝12×216 mm。法蘭與原12孔保持原方向。',31,GRAY)
txt(im,(190,245),'正視圖（沿 X 看，橫向為 Y）',39)
txt(im,(1300,245),'側視圖（沿 Y 看）',39)
txt(im,(1980,245),'法蘭與出口俯視疊圖',39)
s=4.2;baseline=1250
front=lambda y,z:(650+y*s,baseline-z*s)
side=lambda x,z:(1600+x*s,baseline-z*s)
stations=[12+176*j/120 for j in range(121)]+[200]
front_outline=[(-60,0),(60,0),(60,3),(46,3),(46,12)]
front_outline += [(section(z)[0]/2+2,z) for z in stations[1:]]
front_outline += [(-110,200)]+[(-section(z)[0]/2-2,z) for z in reversed(stations[:-1])]
front_outline += [(-46,3),(-60,3),(-60,0)]
side_outline=[(-57,0),(61,0),(61,3),(43,3),(43,12)]
side_outline += [(section(z)[1]/2+2,z) for z in stations[1:]]
side_outline += [(-8,200)]+[(-section(z)[1]/2-2,z) for z in reversed(stations[:-1])]
side_outline += [(-43,3),(-57,3),(-57,0)]
d.line([front(*p) for p in front_outline],fill=INK,width=4)
d.line([side(*p) for p in side_outline],fill=INK,width=4)
d.line([front(-108,200),front(108,200)],fill=BLUE,width=5)
d.line([side(-6,200),side(6,200)],fill=BLUE,width=5)
dim_h(im,front(-108,200)[0],front(108,200)[0],330,front(0,200)[1],'出口淨長 216 mm')
dim_h(im,front(-110,0)[0],front(110,0)[0],1380,baseline,'Y 向最大 220 mm')
dim_v(im,front(0,200)[1],baseline,95,front(-110,200)[0],'200 mm')
dim_h(im,side(-6,200)[0],side(6,200)[0],330,side(0,200)[1],'12 mm')
dim_h(im,side(-57,0)[0],side(61,0)[0],1380,baseline,'X 向最大 118 mm')
txt(im,(1295,1460),'法蘭中心相對風道：X +2 mm',27,GRAY)

t=2.8;cx,cy=2320,840
top=lambda x,y:(cx+y*t,cy+x*t)
d.rounded_rectangle([*top(-57,-60),*top(61,60)],radius=4*t,outline=ORANGE,width=4)
d.rounded_rectangle([*top(-41,-44),*top(41,44)],radius=3*t,outline=GRAY,width=3)
for h in HOLES:
    x,y=top(h['x_mm'],h['y_mm']);radius=h['diameter_mm']/2*t
    d.ellipse((x-radius,y-radius,x+radius,y+radius),outline=INK,width=3)
d.rounded_rectangle([*top(-8,-110),*top(8,110)],radius=2*t,fill=(222,239,248),outline=BLUE,width=3)
d.rectangle([*top(-6,-108),*top(6,108)],fill='white',outline=BLUE,width=3)
dim_h(im,top(0,-108)[0],top(0,108)[0],565,top(-6,0)[1],'出口長邊 216 mm')
dim_v(im,top(-6,0)[1],top(6,0)[1],2670,top(0,108)[0],'12 mm')
txt(im,(2015,1110),'橘：法蘭118×120　灰：入口82×88',27,GRAY)
txt(im,(2015,1160),'藍：出口216×12（空間投影疊合）',27,BLUE)
txt(im,(2015,1210),'角孔4個 Ø6.4；其餘8孔 Ø4.4',27,INK)
txt(im,(2015,1260),'圖面向右 +Y；向下 +X',27,GRAY)
txt(im,(100,1540),'最大包絡 X×Y×Z＝118×220×200 mm｜名義壁厚2 mm｜完整單件｜風向 +Z 直通',34,BLUE)
txt(im,(100,1615),'法蘭118×120×3 mm；核心與十字片配合出口朝向，最後56 mm無分隔。',31,INK)
txt(im,(100,1690),'單位 mm。此為幾何尺寸圖；尚未切片、實印或驗證回流改善。',29,GRAY)
im.save(HERE/'04_橫向出口_尺寸與孔位圖.png',dpi=(220,220))
im.save(HERE/'橫向出口_尺寸與孔位圖.pdf','PDF',resolution=220,title='216x12mm rotated-long-axis nozzle dimensions')

sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
out={'new_manufacturing_blend_sha256':r['blend_sha256'],'new_stl_sha256':r['stl_sha256'],
    'drawing_source':'Verified CAD report and parametric profile; actual CAD renders for direction comparison',
    'registered_flange_projection_mm':{'X':[-57,61],'Y':[-60,60],'R':4,'reference_hole_XY':[52,51]},
    'registered_hole_projections':[{'X':h['x_mm'],'Y':h['y_mm'],'diameter':h['diameter_mm']} for h in HOLES],
    'comparison_camera':preview['comparison_camera'],
    'images':{name:sha(HERE/name) for name in ['03_固定法蘭_新舊出口方向對照.png','04_橫向出口_尺寸與孔位圖.png']}}
(HERE/'圖面來源檢查.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print('REGISTERED_COMPARISON_AND_DIMENSIONS_DONE',flush=True)
