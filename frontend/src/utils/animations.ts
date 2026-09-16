// Advanced animation utilities for enhanced UX

export const celebrationAnimation = () => {
  // Confetti effect for achievements
  const colors = ['#9333ea', '#2563eb', '#16a34a', '#ea580c', '#db2777']
  const confettiCount = 50

  for (let i = 0; i < confettiCount; i++) {
    const confetti = document.createElement('div')
    confetti.className = 'confetti-particle'
    confetti.style.cssText = `
      position: fixed;
      width: 10px;
      height: 10px;
      background: ${colors[Math.floor(Math.random() * colors.length)]};
      top: 50%;
      left: 50%;
      opacity: 1;
      pointer-events: none;
      z-index: 9999;
      border-radius: ${Math.random() > 0.5 ? '50%' : '0'};
    `

    document.body.appendChild(confetti)

    const angle = (Math.PI * 2 * i) / confettiCount
    const velocity = 5 + Math.random() * 10
    const tx = Math.cos(angle) * velocity * 50
    const ty = Math.sin(angle) * velocity * 50 - 100

    confetti.animate([
      { transform: 'translate(0, 0) rotate(0deg)', opacity: 1 },
      { transform: `translate(${tx}px, ${ty}px) rotate(${Math.random() * 360}deg)`, opacity: 0 }
    ], {
      duration: 1000 + Math.random() * 500,
      easing: 'cubic-bezier(0, .9, .57, 1)',
      fill: 'forwards'
    }).onfinish = () => confetti.remove()
  }
}

export const rippleEffect = (e: React.MouseEvent, color: string = '#9333ea') => {
  const target = e.currentTarget as HTMLElement
  const rect = target.getBoundingClientRect()
  const x = e.clientX - rect.left
  const y = e.clientY - rect.top

  const ripple = document.createElement('span')
  ripple.className = 'ripple-effect'
  ripple.style.cssText = `
    position: absolute;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: ${color};
    opacity: 0.6;
    left: ${x}px;
    top: ${y}px;
    transform: translate(-50%, -50%) scale(0);
    pointer-events: none;
  `

  target.style.position = 'relative'
  target.style.overflow = 'hidden'
  target.appendChild(ripple)

  ripple.animate([
    { transform: 'translate(-50%, -50%) scale(0)', opacity: 0.6 },
    { transform: 'translate(-50%, -50%) scale(4)', opacity: 0 }
  ], {
    duration: 600,
    easing: 'ease-out'
  }).onfinish = () => ripple.remove()
}

export const shakeAnimation = (element: HTMLElement) => {
  element.animate([
    { transform: 'translateX(0)' },
    { transform: 'translateX(-10px)' },
    { transform: 'translateX(10px)' },
    { transform: 'translateX(-10px)' },
    { transform: 'translateX(10px)' },
    { transform: 'translateX(0)' }
  ], {
    duration: 400,
    easing: 'ease-in-out'
  })
}

export const pulseGlow = (element: HTMLElement, color: string = '#9333ea') => {
  element.animate([
    { boxShadow: `0 0 0 0 ${color}80` },
    { boxShadow: `0 0 0 10px ${color}00` }
  ], {
    duration: 1000,
    iterations: 3,
    easing: 'ease-out'
  })
}

export const floatAnimation = (element: HTMLElement) => {
  element.animate([
    { transform: 'translateY(0px)' },
    { transform: 'translateY(-10px)' },
    { transform: 'translateY(0px)' }
  ], {
    duration: 2000,
    iterations: Infinity,
    easing: 'ease-in-out'
  })
}

export const typewriterEffect = async (
  element: HTMLElement,
  text: string,
  speed: number = 50
) => {
  element.textContent = ''
  for (let i = 0; i < text.length; i++) {
    element.textContent += text[i]
    await new Promise(resolve => setTimeout(resolve, speed))
  }
}
