import { LocationConfigWizard } from './components/config/LocationConfigWizard'
import { DeviceList } from './components/devices/DeviceList'
import { SensorList } from './features/sensors/SensorList'
import './index.css'

function App() {
  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 text-slate-900 sm:px-6">
      <div className="mx-auto max-w-7xl space-y-8">
        <header>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-emerald-700">
            Greenhouse control
          </p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl">
            Device dashboard
          </h1>
          <p className="mt-2 max-w-2xl text-slate-600">
            Provision and inspect sensor and actuator families for your greenhouse.
          </p>
        </header>
        <section id="configuration">
          <LocationConfigWizard />
        </section>
        <DeviceList />
        <SensorList />
      </div>
    </main>
  )
}

export default App
