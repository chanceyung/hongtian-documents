/**
 * 查找可用端口
 */
import { createServer } from 'net'

export function findFreePort(startPort: number): Promise<number> {
  return new Promise((resolve, reject) => {
    const server = createServer()

    server.listen(startPort, '127.0.0.1', () => {
      const addr = server.address()
      server.close(() => {
        if (addr && typeof addr === 'object') {
          resolve(addr.port)
        } else {
          resolve(startPort)
        }
      })
    })

    server.on('error', () => {
      // 端口被占用，尝试下一个
      if (startPort < 65535) {
        resolve(findFreePort(startPort + 1))
      } else {
        reject(new Error('No available port found'))
      }
    })
  })
}