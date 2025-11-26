import { useState } from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'

import Wallet from './pages/Wallet'

function App() {
  const [count, setCount] = useState(0)


  return (
    <>
    <div
      className='min-h-screen bg-cover bg-center'
      style={{ backgroundColor: 'Black' }}>
     <Wallet />
    </div>
    </>
  )
}

export default App