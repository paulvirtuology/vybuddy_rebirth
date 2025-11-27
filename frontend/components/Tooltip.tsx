'use client'

import { useState, ReactNode } from 'react'

interface TooltipProps {
  content: string
  children: ReactNode
  position?: 'right' | 'left' | 'top' | 'bottom'
}

export default function Tooltip({ content, children, position = 'right' }: TooltipProps) {
  const [isVisible, setIsVisible] = useState(false)

  const positionClasses = {
    right: 'left-full ml-2 top-1/2 -translate-y-1/2',
    left: 'right-full mr-2 top-1/2 -translate-y-1/2',
    top: 'bottom-full mb-2 left-1/2 -translate-x-1/2',
    bottom: 'top-full mt-2 left-1/2 -translate-x-1/2',
  }

  return (
    <div
      className="relative inline-block"
      onMouseEnter={() => setIsVisible(true)}
      onMouseLeave={() => setIsVisible(false)}
    >
      {children}
      {isVisible && (
        <div
          className={`
            absolute z-50 px-3 py-2 text-sm font-medium text-white bg-gray-900 dark:bg-gray-800 rounded-lg shadow-lg
            whitespace-nowrap pointer-events-none transition-all duration-200 ease-in-out
            ${positionClasses[position]}
            opacity-100 scale-100
          `}
        >
          {content}
          {/* Flèche du tooltip */}
          <div
            className={`
              absolute w-2 h-2 bg-gray-900 dark:bg-gray-800 transform rotate-45
              ${
                position === 'right'
                  ? 'left-0 top-1/2 -translate-y-1/2 -translate-x-1/2'
                  : position === 'left'
                  ? 'right-0 top-1/2 -translate-y-1/2 translate-x-1/2'
                  : position === 'top'
                  ? 'bottom-0 left-1/2 -translate-x-1/2 translate-y-1/2'
                  : 'top-0 left-1/2 -translate-x-1/2 -translate-y-1/2'
              }
            `}
          />
        </div>
      )}
    </div>
  )
}

