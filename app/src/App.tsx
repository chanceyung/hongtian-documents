import { Routes, Route } from 'react-router'
import AuthLayout from './components/AuthLayout'
import Home from './pages/Home'
import Login from './pages/Login'
import NotFound from './pages/NotFound'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<AuthLayout><Home /></AuthLayout>} />
      <Route path="/login" element={<Login />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}
