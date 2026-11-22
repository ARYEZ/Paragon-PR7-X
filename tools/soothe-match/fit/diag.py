import os
import fitlib as F, json, sys
t=json.load(open('tuning.json'))
for kv in sys.argv[2:]:
    k,v=kv.split('='); t[k]=float(v)
names=sys.argv[1].split(',')
tot,per,res=F.loss(names,t,os.environ['SOOTHE_DIR'] + '/wdiag')
for n in names:
    g=res[n]['gated']; s=F.soothe(n)['gated']
    print(n,'DOM held %5.1f att %6.1f rel %6.1f | soothe held %5.1f att %6.1f rel %6.1f'%(g['held_cut_db'],g['attack_ms'],g['release_ms'],s['held_cut_db'],s['attack_ms'],s['release_ms']))
json.dump(t,open('trial.json','w'),indent=1)
