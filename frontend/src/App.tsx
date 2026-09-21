import { lazy, Suspense } from "react"
import { Navigate, Route, Routes } from "react-router-dom"
import ProtectedRoute from "./components/ProtectedRoute"
import Layout from "./components/Layout"
import LandingPage from "./pages/LandingPage"
import AuthPage from "./pages/AuthPage"
import DashboardPage from "./pages/DashboardPage"
import ClassroomPage from "./pages/ClassroomPage"
import ProgressPage from "./pages/ProgressPage"
import ProfilePage from "./pages/ProfilePage"
import ModuleWorkspacePage from "./pages/ModuleWorkspacePage"
import ChatPage from "./pages/ChatPage"
import FlashCoursePage from "./pages/FlashCoursePage"
import LibraryPage from "./pages/LibraryPage"
import BillingReturnPage from "./pages/BillingReturnPage"
import ManagerRoute from "./components/ManagerRoute"

// El panel de gerencia se carga aparte y solo cuando alguien entra en él:
// ningún alumno necesita descargar sus gráficos, y en el mismo paquete
// hacía pasar el JavaScript inicial de la app de los 500 kB.
const ManagementLayout = lazy(() => import("./components/management/ManagementLayout"))
const OverviewPage = lazy(() => import("./pages/management/OverviewPage"))
const EngagementPage = lazy(() => import("./pages/management/EngagementPage"))
const JourneyPage = lazy(() => import("./pages/management/JourneyPage"))
const RetentionPage = lazy(() => import("./pages/management/RetentionPage"))
const RevenuePage = lazy(() => import("./pages/management/RevenuePage"))
const CustomersPage = lazy(() => import("./pages/management/CustomersPage"))
const CustomerDetailPage = lazy(() => import("./pages/management/CustomerDetailPage"))
const SystemPage = lazy(() => import("./pages/management/SystemPage"))

function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<AuthPage />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/classroom" element={<ClassroomPage />} />
          <Route path="/progress" element={<ProgressPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/modules/:moduleId" element={<ModuleWorkspacePage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/library" element={<LibraryPage />} />
          <Route path="/library/:slug" element={<FlashCoursePage />} />
          {/* A dónde vuelve el alumno desde Stripe/PayPal (app/billing/*). */}
          <Route path="/billing/success" element={<BillingReturnPage outcome="success" />} />
          <Route path="/billing/cancel" element={<BillingReturnPage outcome="cancel" />} />
        </Route>
      </Route>

      {/* Panel de gerencia: solo lectura, rol "manager" o "admin". */}
      <Route element={<ManagerRoute />}>
        <Route
          element={
            <Suspense fallback={<div className="min-h-screen bg-slate-50" />}>
              <ManagementLayout />
            </Suspense>
          }
        >
          <Route path="/gerencia" element={<OverviewPage />} />
          <Route path="/gerencia/consumo" element={<EngagementPage />} />
          <Route path="/gerencia/journey" element={<JourneyPage />} />
          <Route path="/gerencia/retencion" element={<RetentionPage />} />
          <Route path="/gerencia/ingresos" element={<RevenuePage />} />
          <Route path="/gerencia/clientes" element={<CustomersPage />} />
          <Route path="/gerencia/clientes/:customerId" element={<CustomerDetailPage />} />
          <Route path="/gerencia/sistema" element={<SystemPage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
