import json, re, sys, urllib.request, urllib.parse, concurrent.futures as cf, ssl
from html.parser import HTMLParser
UA="Mozilla/5.0 (human.json research crawler)"
class P(HTMLParser):
    def __init__(s): super().__init__(); s.hrefs=[]
    def handle_starttag(s,t,a):
        if t=='link':
            d=dict(a); rel=(d.get('rel') or '').lower().split()
            if 'human-json' in rel and d.get('href'): s.hrefs.append(d['href'])
def get(u,n=1500000):
    r=urllib.request.Request(u,headers={'User-Agent':UA,'Accept':'*/*'})
    with urllib.request.urlopen(r,timeout=15) as f:
        return f.geturl(), f.read(n), dict(f.headers)
def norm(u):
    p=urllib.parse.urlsplit(u.strip())
    if p.scheme not in('http','https') or not p.hostname: return None
    host=p.hostname.lower()
    if p.port and not((p.scheme=='http' and p.port==80) or (p.scheme=='https' and p.port==443)): host+=':%d'%p.port
    return f"{p.scheme}://{host}{p.path.rstrip('/')}"
def probe(site):
    res={'site':site}
    try:
        final,body,h=get(site if site.count('/')>2 else site+'/')
        res['final']=final
        p=P(); p.feed(body.decode('utf-8','replace'))
        lh=h.get('Link') or h.get('link') or ''
        res['link_header']= 'human-json' in lh
        if p.hrefs: hj=urllib.parse.urljoin(final,p.hrefs[0]); res['via']='link'
        else:
            res['via']='fallback'; hj=None
            for cand in ['/human.json','/.well-known/human.json']:
                try:
                    u=urllib.parse.urljoin(final,cand); _,b,_=get(u); d=json.loads(b)
                    if 'url' in d: hj=u; break
                except Exception: pass
        if not hj: res['status']='no-human-json'; return res
        res['hj']=hj
        _,b,hh=get(hj); d=json.loads(b.decode('utf-8-sig'))
        res['cors']=hh.get('Access-Control-Allow-Origin'); res['ctype']=hh.get('Content-Type')
        res['version']=d.get('version'); res['url']=d.get('url')
        res['vouches']=[(v.get('url'),v.get('vouched_at')) for v in d.get('vouches',[]) if isinstance(v,dict)]
        res['extra_keys']=[k for k in d if k not in('version','url','vouches')]
        res['status']='ok'
    except Exception as e:
        res['status']='err:'+type(e).__name__+':'+str(e)[:80]
    return res
if __name__=='__main__':
    seeds=[l.strip() for l in open(sys.argv[1]) if l.strip()]
    maxn=int(sys.argv[2]) if len(sys.argv)>2 else 3000
    seen={}; frontier=[norm(s) for s in seeds if norm(s)]; depth=0
    while frontier and len(seen)<maxn:
        frontier=[f for f in dict.fromkeys(frontier) if f not in seen]
        with cf.ThreadPoolExecutor(32) as ex:
            out=list(ex.map(probe,frontier))
        nxt=[]
        for r in out:
            seen[r['site']]=r
            for u,_ in r.get('vouches',[]):
                if isinstance(u,str) and norm(u) and norm(u) not in seen: nxt.append(norm(u))
        print('depth',depth,'probed',len(frontier),'total',len(seen),'ok',sum(1 for r in seen.values() if r['status']=='ok'),file=sys.stderr)
        frontier=nxt; depth+=1
    json.dump(seen,open(sys.argv[3] if len(sys.argv)>3 else 'graph.json','w'),indent=1)
