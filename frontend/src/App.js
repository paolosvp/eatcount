import React, { useEffect, useRef, useState } from 'react';
import './App.css';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL; // do not hardcode
const API = `${BACKEND_URL}/api`;

function useAuth() {
  const [token, setToken] = useState(localStorage.getItem('token') || '');
  const [email, setEmail] = useState(localStorage.getItem('email') || '');

  const save = (t, e) => {
    localStorage.setItem('token', t);
    localStorage.setItem('email', e || email);
    setToken(t);
    setEmail(e || email);
  };
  const clear = () => { localStorage.removeItem('token'); localStorage.removeItem('email'); setToken(''); setEmail(''); };

  return { token, email, save, clear };
}

function Section({ children }) {
  return <div className="container" style={{marginTop: 24}}>{children}</div>;
}

function Hero() {
  return (
    <div className="hero-section">
      <div className="container">
        <h1 className="hero-title">Snap. Estimate. Stay on Track.</h1>
        <p className="hero-subtitle">Capture your meal and get an instant calorie estimate. Set a daily target based on your profile.</p>
        <div style={{display:'flex', gap:12, justifyContent:'center'}}>
          <a className="btn-primary" href="#scan">Scan a Meal</a>
          <a className="btn-secondary" href="#profile">Set Daily Target</a>
        </div>
      </div>
    </div>
  );
}

function AuthPanel({ auth }) {
  const [form, setForm] = useState({ email: '', password: '' });
  const [mode, setMode] = useState('login');
  const [msg, setMsg] = useState('');

  const submit = async (e) => {
    e.preventDefault(); setMsg('');
    try {
      const url = mode === 'login' ? `${API}/auth/login` : `${API}/auth/register`;
      const res = await axios.post(url, form);
      auth.save(res.data.access_token, form.email);
      setMsg('Success');
    } catch (err) {
      setMsg(err?.response?.data?.detail || err.message);
    }
  };

  return (
    <div className="card">
      <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
        <h3 style={{margin:0}}>Account</h3>
        {auth.token ? <button className="btn-secondary" onClick={auth.clear}>Logout</button> : null}
      </div>
      {!auth.token && (
        <form onSubmit={submit} style={{marginTop:12}}>
          <div className="row">
            <label className="label">Email</label>
            <input className="input" type="email" value={form.email} onChange={e=>setForm({...form, email:e.target.value})} required />
          </div>
          <div className="row" style={{marginTop:8}}>
            <label className="label">Password</label>
            <input className="input" type="password" value={form.password} onChange={e=>setForm({...form, password:e.target.value})} required minLength={6} />
          </div>
          <div style={{display:'flex', gap:8, marginTop:12}}>
            <button className="btn-primary" type="submit">{mode==='login'?'Login':'Register'}</button>
            <button className="btn-secondary" type="button" onClick={()=>setMode(mode==='login'?'register':'login')}>
              Switch to {mode==='login'?'Register':'Login'}
            </button>
          </div>
          {msg && <div style={{marginTop:8}} className={msg==='Success'? 'success':'error'}>{msg}</div>}
        </form>
      )}
      {auth.token && <div className="small">Logged in as {auth.email}</div>}
    </div>
  );
}

function ProfilePanel({ auth }) {
  const [profile, setProfile] = useState(null);
  const [form, setForm] = useState({ height_cm:'', weight_kg:'', age:'', gender:'male', activity_level:'light', goal:'maintain', goal_intensity:'moderate', goal_weight_kg:'' });
  const [msg, setMsg] = useState('');

  const headers = auth.token ? { Authorization: `Bearer ${auth.token}` } : {};

  const fetchMe = async () => {
    if (!auth.token) return;
    try {
      const res = await axios.get(`${API}/profile/me`, { headers });
      setProfile(res.data.profile);
    } catch (e) { /* ignore */ }
  };

  useEffect(()=>{ fetchMe(); }, [auth.token]);

  const submit = async (e) => {
    e.preventDefault(); setMsg('');
    if (!auth.token) { setMsg('Login required'); return; }
    try {
      const payload = {
        ...form,
        height_cm: parseFloat(form.height_cm),
        weight_kg: parseFloat(form.weight_kg),
        age: parseInt(form.age, 10),
        goal_weight_kg: form.goal_weight_kg? parseFloat(form.goal_weight_kg): null
      };
      const res = await axios.put(`${API}/profile`, payload, { headers });
      setProfile(res.data.profile);
      setMsg('Saved');
    } catch (err) {
      setMsg(err?.response?.data?.detail || err.message);
    }
  };

  return (
    <div id="profile" className="card">
      <h3 style={{marginTop:0}}>Daily Target</h3>
      <form onSubmit={submit}>
        <div className="row row-3">
          <div>
            <label className="label">Height (cm)</label>
            <input className="input" value={form.height_cm} onChange={e=>setForm({...form, height_cm: e.target.value})} required type="number" step="0.1" />
          </div>
          <div>
            <label className="label">Weight (kg)</label>
            <input className="input" value={form.weight_kg} onChange={e=>setForm({...form, weight_kg: e.target.value})} required type="number" step="0.1" />
          </div>
          <div>
            <label className="label">Age</label>
            <input className="input" value={form.age} onChange={e=>setForm({...form, age: e.target.value})} required type="number" />
          </div>
          <div>
            <label className="label">Gender</label>
            <select className="input" value={form.gender} onChange={e=>setForm({...form, gender:e.target.value})}>
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div>
            <label className="label">Activity</label>
            <select className="input" value={form.activity_level} onChange={e=>setForm({...form, activity_level:e.target.value})}>
              <option value="sedentary">Sedentary</option>
              <option value="light">Light</option>
              <option value="moderate">Moderate</option>
              <option value="very">Very</option>
              <option value="extra">Extra</option>
            </select>
          </div>
          <div>
            <label className="label">Goal</label>
            <select className="input" value={form.goal} onChange={e=>setForm({...form, goal:e.target.value})}>
              <option value="lose">Lose</option>
              <option value="maintain">Maintain</option>
              <option value="gain">Gain</option>
            </select>
          </div>
          <div>
            <label className="label">Intensity</label>
            <select className="input" value={form.goal_intensity} onChange={e=>setForm({...form, goal_intensity:e.target.value})}>
              <option value="mild">Mild</option>
              <option value="moderate">Moderate</option>
              <option value="aggressive">Aggressive</option>
            </select>
          </div>
          <div>
            <label className="label">Goal Weight (kg)</label>
            <input className="input" value={form.goal_weight_kg} onChange={e=>setForm({...form, goal_weight_kg:e.target.value})} type="number" step="0.1" />
          </div>
        </div>
        <div style={{marginTop: 12, display:'flex', gap:8}}>
          <button className="btn-primary" type="submit">Save &amp; Compute</button>
          {profile && <div className="small">Recommended: <b>{profile.recommended_daily_calories}</b> kcal/day</div>}
        </div>
        <div className="small" style={{marginTop:8}}>{profile? 'Last updated: '+ (profile.updated_at || ''): ''}</div>
        {profile && (
          <div className="card" style={{marginTop:12}}>
            <div className="small">Summary</div>
            <div style={{fontSize:16}}><b>{profile.recommended_daily_calories}</b> kcal/day target</div>
          </div>
        )}
        {msg && <div style={{marginTop:8}} className={msg==='Saved'?'success':'error'}>{msg}</div>}
      </form>
    </div>
  );
}

function DayLogPanel({ auth, refreshKey, optimisticAdd }) {
  const localDateStr = (d = new Date()) => {
    const tz = d.getTimezoneOffset();
    const local = new Date(d.getTime() - tz * 60000);
    return local.toISOString().slice(0, 10);
  };
  const [date, setDate] = useState(() => localDateStr());
  const [meals, setMeals] = useState([]);
  const [total, setTotal] = useState(0);
  const [target, setTarget] = useState(null);
  const [streak, setStreak] = useState({ current_streak_days: 0, best_streak_days: 0 });
  const [pending, setPending] = useState([]); // optimistic meals not yet seen from server
  const headers = auth.token ? { Authorization: `Bearer ${auth.token}` } : {};

  const fetchMeals = async () => {
    if (!auth.token) { setMeals([]); setTotal(0); setTarget(null); setPending([]); return; }
    try {
      const tz = new Date().getTimezoneOffset();
      const [mealsRes, profileRes, streakRes] = await Promise.all([
        axios.get(`${API}/meals`, { params: { date, tz_offset_minutes: tz }, headers }),
        axios.get(`${API}/profile/me`, { headers }),
        axios.get(`${API}/meals/stats`, { headers })
      ]);
      const serverMeals = mealsRes.data.meals || [];
      setMeals(serverMeals);
      setTotal(mealsRes.data.daily_total || 0);
      setTarget(profileRes.data.profile?.recommended_daily_calories || null);
      setStreak(streakRes.data || { current_streak_days: 0, best_streak_days: 0 });
      // Drop pending items that are now present in server list
      setPending((p) => {
        const ids = new Set(serverMeals.map(x => x.id));
        return p.filter(x => !x.id || !ids.has(x.id));
      });
    } catch (e) {
      setMeals([]); setTotal(0); setTarget(null);
    }
  };

  useEffect(()=>{ fetchMeals(); }, [auth.token, date, refreshKey]);

  // Optimistic add: only if the saved meal is for the currently viewed date (assume today)
  useEffect(() => {
    if (!optimisticAdd) return;
    const isSameDay = (localDateStr() === date);
    if (!isSameDay) return;
    setPending((p)=>{
      const exists = p.some(x => x.id === optimisticAdd.id);
      if (exists) return p;
      const entry = {
        id: optimisticAdd.id || `temp-${Date.now()}`,
        total_calories: Number(optimisticAdd.total_calories||0),
        items: Array.isArray(optimisticAdd.items)? optimisticAdd.items: [],
        notes: optimisticAdd.notes || '',
        image_base64: optimisticAdd.image_base64 || '',
        created_at: optimisticAdd.created_at || new Date().toISOString()
      };
      return [entry, ...p];
    });
  }, [optimisticAdd, date]);

  const remove = async (id) => {
    if (!auth.token) return;
    try {
      await axios.delete(`${API}/meals/${id}`, { headers });
      await fetchMeals();
    } catch (e) { /* ignore */ }
  };

  // Compose pending + server meals for display; adjust total accordingly to avoid flicker
  const pendingTotal = pending.reduce((acc, m) => acc + Number(m.total_calories||0), 0);
  const displayMeals = [...pending, ...meals];
  const displayTotal = Math.round((Number(total||0) + pendingTotal) * 100) / 100;
  const pct = target ? Math.min(100, Math.round((displayTotal/target)*100)) : null;

  return (
    <div className="card">
      <h3 style={{marginTop:0}}>Day Log</h3>
      <div style={{display:'flex', gap:8, alignItems:'center', flexWrap:'wrap'}}>
        <input className="input" type="date" value={date} onChange={e=>setDate(e.target.value)} />
        <div className="small">Total: <b>{Math.round(displayTotal)}</b> kcal {target ? `(of ${target})` : ''}</div>
        {target !== null && (
          <div style={{flexBasis:'100%', marginTop:6}}>
            <div style={{height:10, borderRadius:6, background:'rgba(24,24,24,0.08)', overflow:'hidden'}}>
              <div style={{width: `${pct}%`, height:'100%', background:'rgb(0,128,255)'}} />
            </div>
            <div className="small" style={{marginTop:4}}>{pct}% of daily target</div>
          </div>
        )}
        <div className="small">Streak: <b>{streak.current_streak_days}</b> days (best {streak.best_streak_days})</div>
      </div>
      <div className="items-list" style={{marginTop:8}}>
        {displayMeals.length === 0 && <div className="small">No entries for this day.</div>}
        {displayMeals.map((m) => (
          <div key={m.id} className="item-row" style={{alignItems:'flex-start', gap:8}}>
            <div style={{display:'flex', gap:10, alignItems:'flex-start'}}>
              {m.image_base64 && (
                <img src={`data:image/jpeg;base64,${m.image_base64}`} alt="meal" style={{width:64, height:64, objectFit:'cover', borderRadius:8, border:'1px solid var(--border-light)'}} />
              )}
              <div>
                <div><b>{Math.round(m.total_calories)}</b> kcal</div>
                <div className="small">{new Date(m.created_at).toLocaleTimeString()}</div>
                {m.notes && <div className="small">{m.notes}</div>}
              </div>
            </div>
            <div style={{textAlign:'right', flex:1}}>
              <div className="small">Items</div>
              <div className="small">
                {m.items.map((it, idx)=> (
                  <div key={idx}>{it.name} • {it.quantity_units} • {Math.round(it.calories)} kcal</div>
                ))}
              </div>
            </div>
            <div>
              <button className="btn-secondary" onClick={()=>remove(m.id)}>Delete</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ScannerPanel({ auth, onSaved }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [streaming, setStreaming] = useState(false);
  const [snapshot, setSnapshot] = useState('');
  const [desc, setDesc] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [simulate, setSimulate] = useState(() => {
    const saved = localStorage.getItem('simulate_mode');
    return saved ? saved === 'true' : true; // default ON
  });
  const [apiKey, setApiKey] = useState('');

  useEffect(()=>{
    // nothing initially
  }, []);

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: false });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
        setStreaming(true);
      }
    } catch (e) {
      setError('Camera access denied or unavailable');
    }
  };

  const stopCamera = () => {
    const v = videoRef.current;
    if (v && v.srcObject) {
      const tracks = v.srcObject.getTracks();
      tracks.forEach(t => t.stop());
      v.srcObject = null;
    }
    setStreaming(false);
  };

  const capture = () => {
    const v = videoRef.current;
    const c = canvasRef.current;
    if (!v || !c) return;
    const w = v.videoWidth || 640; const h = v.videoHeight || 480;
    c.width = w; c.height = h;
    const ctx = c.getContext('2d');
    ctx.drawImage(v, 0, 0, w, h);
    const dataUrl = c.toDataURL('image/jpeg', 0.9);
    const base64 = dataUrl.split(',')[1];
    setSnapshot(base64);
  };

  const estimate = async () => {
    setLoading(true); setError(''); setResult(null);
    try {
      const payload = { message: desc, images: [{ data: snapshot, mime_type: 'image/jpeg', filename: 'capture.jpg' }], simulate, api_key: apiKey !== '' ? apiKey : undefined };
      const res = await axios.post(`${API}/ai/estimate-calories`, payload);
      setResult(res.data);
      // Key mode banner based on engine_info
      if (res.data?.engine_info?.key_mode === 'provided') {
        console.log('Using provided API key');
      } else if (res.data?.engine_info?.key_mode === 'emergent') {
        console.log('Using Emergent LLM Key');
      } else if (simulate) {
        console.log('Simulated mode');
      }
    } catch (e) {
      setError(e?.response?.data?.detail || e.message);
    } finally { setLoading(false); }
  };

  const saveLog = async () => {
    if (!auth.token) { setError('Login required to save'); return; }
    if (!result) { setError('No estimate to save'); return; }
    try {
      const headers = { Authorization: `Bearer ${auth.token}` };
      // Normalize items to backend schema defensively
      const normalizeItem = (it) => ({
        name: String(it?.name || '').trim() || 'Item',
        quantity_units: String(it?.quantity_units || it?.quantity || it?.portion || '').trim(),
        calories: Number(it?.calories || 0),
        confidence: Math.max(0, Math.min(1, Number(it?.confidence ?? 0.7)))
      });
      const normItems = Array.isArray(result.items) ? result.items.map(normalizeItem) : [];
      const total = Number(result.total_calories || 0);
      const payload = {
        total_calories: total,
        items: normItems,
        notes: (desc || result.notes || '').toString(),
        image_base64: snapshot,
      };
      const { data } = await axios.post(`${API}/meals`, payload, { headers });
      onSaved && onSaved(data);
      setError('');
    } catch (e) {
      setError(e?.response?.data?.detail || e.message);
    }
  };

  const onFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result;
      const b64 = String(dataUrl).split(',')[1];
      setSnapshot(b64);
    };
    reader.readAsDataURL(file);
  };

  return (
    <div id="scan" className="card">
      <h3 style={{marginTop:0}}>Scan a Meal</h3>
      <div className="camera-wrapper">
        <video ref={videoRef} className={streaming? 'video-el':'hidden-video'} playsInline muted></video>
        <canvas ref={canvasRef} className="hidden-video"></canvas>
        <div style={{display:'flex', gap:8, flexWrap:'wrap'}}>
          {!streaming ? (
            <button className="btn-primary" onClick={startCamera}>Start Camera</button>
          ) : (
            <>
              <button className="btn-primary" onClick={capture}>Capture</button>
              <button className="btn-secondary" onClick={stopCamera}>Stop</button>
            </>
          )}
          <label className="btn-secondary" style={{cursor:'pointer'}}>
            Upload Image
            <input type="file" accept="image/*" onChange={onFile} style={{display:'none'}} />
          </label>
        </div>
        {snapshot && (
          <div>
            <img className="preview-img" src={`data:image/jpeg;base64,${snapshot}`} alt="preview" />
          </div>
        )}
        <div className="row" style={{marginTop:8}}>
          <label className="label">Add a description (optional)</label>
          <textarea className="input" rows={3} placeholder="e.g. No dressing, medium portion"
            value={desc} onChange={e=>setDesc(e.target.value)} />
        </div>
        <div style={{display:'flex', gap:8, alignItems:'center', flexWrap:'wrap'}}>
          <button className="btn-primary" disabled={!snapshot || loading} onClick={estimate}>{loading? 'Estimating...':'Estimate Calories'}</button>
          <label className="small" style={{display:'inline-flex', alignItems:'center', gap:6}}>
            <input type="checkbox" checked={simulate} onChange={e=>{setSimulate(e.target.checked); localStorage.setItem('simulate_mode', String(e.target.checked));}} /> Test mode (no API key)
          </label>
          <span className="small" aria-label="inference-mode" style={{padding:'6px 10px', border:'1px solid var(--border-light)', borderRadius: 8}}>Mode: {simulate ? 'Simulated' : 'Live'}</span>
          <input className="input" style={{maxWidth:300, display: simulate ? 'none' : 'block'}} type="password" placeholder="Enter API key or leave blank to use Emergent LLM Key"
            value={apiKey} onChange={e=>setApiKey(e.target.value)} />
        </div>
        {error && <div className="error" style={{marginTop:8}}>{error}</div>}
        {result && (
          <div className="card" style={{marginTop:12}}>
            <div className="small">Confidence: {result.confidence !== undefined ? (result.confidence*100).toFixed(0) : '—'}%</div>
            <h4 style={{margin:'8px 0'}}>Total: {Math.round(Number(result.total_calories || 0))} kcal</h4>
            <div className="items-list">
              {(Array.isArray(result.items) ? result.items : []).map((it, idx)=> (
                <div className="item-row" key={idx}>
                  <div>{(it?.name||'Item')} • {(it?.quantity_units||it?.quantity||it?.portion||'')}</div>
                  <div><b>{Math.round(Number(it?.calories||0))}</b> kcal</div>
                </div>
              ))}
            </div>
            {result.notes && <div className="small" style={{marginTop:8}}>{String(result.notes)}</div>}
            {auth.token && (
              <div style={{marginTop:8}}>
                <button className="btn-secondary" onClick={saveLog}>Save to Day Log</button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default function App(){
  const auth = useAuth();
  const [logRefreshKey, setLogRefreshKey] = useState(0);
  const [optimisticSave, setOptimisticSave] = useState(null); // last saved meal


  useEffect(()=>{
    (async ()=>{
      try { await axios.get(`${API}/`); } catch (e) { /* ignore in UI */ }
    })();
  }, []);

  return (
    <>
      <Hero />
      <Section>
        <div className="nav">
          <a className="nav-link" href="#scan">Scan</a>
          <a className="nav-link" href="#profile">Profile</a>
          <a className="nav-link" href="#account">Account</a>
        </div>
        <div className="row row-2">
          <div id="account"><AuthPanel auth={auth} /></div>
          <div><ProfilePanel auth={auth} /></div>
        </div>
        <div style={{marginTop:16}}>
          <ScannerPanel auth={auth} onSaved={(saved) => { setOptimisticSave(saved); setLogRefreshKey(k=>k+1); }} />
        </div>
        <div style={{marginTop:16}}>
          <DayLogPanel auth={auth} refreshKey={logRefreshKey} optimisticAdd={optimisticSave} />
        </div>
        <div className="footer-space" />
      </Section>
    </>
  );
}