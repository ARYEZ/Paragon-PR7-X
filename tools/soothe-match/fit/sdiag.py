import os
import fitlib as F, json, sys
t=json.load(open('tuning.json'))
for kv in sys.argv[2:]:
    k,v=kv.split('='); t[k]=float(v)
names=sys.argv[1].split(',')
tot,per,res=F.loss(names,t,os.environ['SOOTHE_DIR'] + '/wdiag')
keys=['fix150','fix400','fix1000','fix3500','fix8000','fixw3500','sw250','sw500','sw1000','sw2000','sw4000','sw8000','sw12000','flat_deep','lv40','lv10','snare','lr_left_1k5_db','lr_right_5k_db','side_side_3k_db']
print('%-5s'%''+''.join('%9s'%k[-9:] for k in keys))
for n in names:
    a=F.features(res[n]); b=F.features(F.soothe(n))
    print('%-5s'%n+''.join('%9.1f'%a[k] for k in keys))
    print('%-5s'%'  s'+''.join('%9.1f'%b[k] for k in keys))
json.dump(t,open('trial.json','w'),indent=1)
