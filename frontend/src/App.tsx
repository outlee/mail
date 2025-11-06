import { Route, Routes } from 'react-router-dom'
import { Layout } from 'antd'
import Dashboard from './pages/Dashboard'
import './App.css'

const { Header, Content } = Layout

function App() {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ color: 'white', fontSize: '20px', fontWeight: 'bold' }}>
        MTBF Platform
      </Header>
      <Content style={{ padding: '24px' }}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
        </Routes>
      </Content>
    </Layout>
  )
}

export default App
