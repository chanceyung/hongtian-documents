import { Routes, Route } from 'react-router'
import AuthLayout from './components/AuthLayout'
import Home from './pages/Home'
import NotFound from './pages/NotFound'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<AuthLayout><Home /></AuthLayout>} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}