/**
 * Script loader pour le widget VyBuddy Chat
 * 
 * Usage:
 * <script src="https://votre-chatbot.com/chat-widget.js"></script>
 * <script>
 *   VyBuddyWidget.init({
 *     chatbotUrl: 'https://votre-chatbot.com',
 *     position: 'bottom-right',
 *     buttonColor: '#6366f1',
 *     buttonSize: 'large'
 *   });
 * </script>
 */

(function() {
  'use strict';

  // Configuration par défaut
  const defaultConfig = {
    chatbotUrl: window.location.origin,
    position: 'bottom-right',
    buttonColor: '#6366f1',
    buttonSize: 'large',
    zIndex: 9999,
  };

  // État du widget
  let widgetConfig = {};
  let isOpen = false;
  let iframe = null;
  let button = null;
  let container = null;

  // Positions possibles
  const positions = {
    'bottom-right': { bottom: '1rem', right: '1rem' },
    'bottom-left': { bottom: '1rem', left: '1rem' },
    'top-right': { top: '1rem', right: '1rem' },
    'top-left': { top: '1rem', left: '1rem' },
  };

  // Tailles de bouton
  const buttonSizes = {
    small: { width: '48px', height: '48px', iconSize: '24px' },
    medium: { width: '56px', height: '56px', iconSize: '28px' },
    large: { width: '64px', height: '64px', iconSize: '32px' },
  };

  /**
   * Crée le bouton flottant
   */
  function createButton() {
    if (button) return;

    const size = buttonSizes[widgetConfig.buttonSize] || buttonSizes.large;
    const position = positions[widgetConfig.position] || positions['bottom-right'];

    button = document.createElement('button');
    button.setAttribute('aria-label', 'Ouvrir le chat VyBuddy');
    button.setAttribute('type', 'button');
    button.style.cssText = `
      position: fixed;
      ${position.top ? `top: ${position.top};` : ''}
      ${position.bottom ? `bottom: ${position.bottom};` : ''}
      ${position.left ? `left: ${position.left};` : ''}
      ${position.right ? `right: ${position.right};` : ''}
      width: ${size.width};
      height: ${size.height};
      background-color: ${widgetConfig.buttonColor};
      color: white;
      border: none;
      border-radius: 50%;
      cursor: pointer;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
      z-index: ${widgetConfig.zIndex};
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.3s ease;
    `;

    button.addEventListener('mouseenter', function() {
      this.style.transform = 'scale(1.1)';
      this.style.boxShadow = '0 6px 16px rgba(0, 0, 0, 0.2)';
    });

    button.addEventListener('mouseleave', function() {
      this.style.transform = 'scale(1)';
      this.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.15)';
    });

    // Icône SVG
    const iconSize = size.iconSize;
    button.innerHTML = `
      <svg width="${iconSize}" height="${iconSize}" fill="none" viewBox="0 0 24 24" stroke="currentColor" style="pointer-events: none;">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
      </svg>
    `;

    button.addEventListener('click', toggleWidget);
    document.body.appendChild(button);
  }

  /**
   * Crée le conteneur iframe
   */
  function createContainer() {
    if (container) return;

    container = document.createElement('div');
    
    // Position par défaut (desktop)
    const position = positions[widgetConfig.position] || positions['bottom-right'];
    const isMobile = window.matchMedia('(max-width: 640px)').matches;
    
    if (isMobile) {
      // Mobile : fullscreen-like
      container.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        width: 100vw;
        height: 100vh;
        z-index: ${widgetConfig.zIndex - 1};
        display: none;
        box-shadow: none;
        border-radius: 0;
        overflow: hidden;
        background: white;
      `;
    } else {
      // Desktop : fenêtre flottante
      container.style.cssText = `
        position: fixed;
        ${position.top ? `top: ${position.top};` : ''}
        ${position.bottom ? `bottom: ${position.bottom === '1rem' ? '80px' : position.bottom};` : ''}
        ${position.left ? `left: ${position.left};` : ''}
        ${position.right ? `right: ${position.right};` : ''}
        width: 384px;
        height: 600px;
        max-width: calc(100vw - 2rem);
        max-height: calc(100vh - 6rem);
        z-index: ${widgetConfig.zIndex - 1};
        display: none;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
        border-radius: 0.5rem;
        overflow: hidden;
        background: white;
      `;
    }

    // Responsive pour mobile
    const mediaQuery = window.matchMedia('(max-width: 640px)');
    function handleResize(e) {
      if (e.matches) {
        // Mobile : fullscreen
        container.style.top = '0';
        container.style.left = '0';
        container.style.right = '0';
        container.style.bottom = '0';
        container.style.width = '100vw';
        container.style.height = '100vh';
        container.style.borderRadius = '0';
        container.style.boxShadow = 'none';
      } else {
        // Desktop : fenêtre flottante
        const pos = positions[widgetConfig.position] || positions['bottom-right'];
        container.style.top = pos.top || 'auto';
        container.style.left = pos.left || 'auto';
        container.style.right = pos.right || 'auto';
        container.style.bottom = pos.bottom === '1rem' ? '80px' : (pos.bottom || 'auto');
        container.style.width = '384px';
        container.style.height = '600px';
        container.style.borderRadius = '0.5rem';
        container.style.boxShadow = '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)';
      }
    }
    
    // Utiliser addEventListener pour la compatibilité moderne
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handleResize);
    } else {
      // Fallback pour anciens navigateurs
      mediaQuery.addListener(handleResize);
    }
    handleResize(mediaQuery);

    iframe = document.createElement('iframe');
    iframe.src = widgetConfig.chatbotUrl + '/widget';
    iframe.style.cssText = `
      width: 100%;
      height: 100%;
      border: none;
      display: block;
    `;
    iframe.setAttribute('allow', 'microphone; camera');

    // Écouter les messages de l'iframe
    window.addEventListener('message', handleIframeMessage);

    container.appendChild(iframe);
    document.body.appendChild(container);
  }

  /**
   * Gère les messages de l'iframe
   */
  function handleIframeMessage(event) {
    // Vérifier l'origine pour la sécurité
    if (!event.origin.startsWith(widgetConfig.chatbotUrl)) return;

    if (event.data.type === 'VYBUDDY_WIDGET_CLOSE') {
      closeWidget();
    }
  }

  /**
   * Ouvre le widget
   */
  function openWidget() {
    if (isOpen) return;

    isOpen = true;
    createContainer();
    
    if (container) {
      container.style.display = 'block';
    }

    if (button) {
      button.innerHTML = `
        <svg width="${buttonSizes[widgetConfig.buttonSize]?.iconSize || '32px'}" height="${buttonSizes[widgetConfig.buttonSize]?.iconSize || '32px'}" fill="none" viewBox="0 0 24 24" stroke="currentColor" style="pointer-events: none;">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      `;
    }

    // Envoyer un message à l'iframe pour l'initialiser
    if (iframe && iframe.contentWindow) {
      iframe.contentWindow.postMessage(
        {
          type: 'VYBUDDY_WIDGET_INIT',
          options: widgetConfig,
        },
        widgetConfig.chatbotUrl
      );
    }
  }

  /**
   * Ferme le widget
   */
  function closeWidget() {
    if (!isOpen) return;

    isOpen = false;

    if (container) {
      container.style.display = 'none';
    }

    if (button) {
      const size = buttonSizes[widgetConfig.buttonSize] || buttonSizes.large;
      button.innerHTML = `
        <svg width="${size.iconSize}" height="${size.iconSize}" fill="none" viewBox="0 0 24 24" stroke="currentColor" style="pointer-events: none;">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
        </svg>
      `;
    }
  }

  /**
   * Toggle le widget
   */
  function toggleWidget() {
    if (isOpen) {
      closeWidget();
    } else {
      openWidget();
    }
  }

  /**
   * Initialise le widget
   */
  function init(config) {
    widgetConfig = Object.assign({}, defaultConfig, config);

    // Créer le bouton
    createButton();

    // Créer le conteneur (mais ne pas l'afficher)
    createContainer();
  }

  /**
   * Détruit le widget
   */
  function destroy() {
    if (button && button.parentNode) {
      button.parentNode.removeChild(button);
      button = null;
    }
    if (container && container.parentNode) {
      container.parentNode.removeChild(container);
      container = null;
    }
    iframe = null;
    isOpen = false;
  }

  // Exposer l'API globale
  window.VyBuddyWidget = {
    init: init,
    open: openWidget,
    close: closeWidget,
    toggle: toggleWidget,
    destroy: destroy,
  };

  // Auto-initialisation si des paramètres sont détectés dans l'URL du script
  (function autoInit() {
    // Trouver le script actuel
    const scripts = document.getElementsByTagName('script');
    let currentScript = null;
    for (let i = 0; i < scripts.length; i++) {
      if (scripts[i].src && scripts[i].src.includes('chat-widget.js')) {
        currentScript = scripts[i];
        break;
      }
    }

    if (!currentScript) return;

    // Extraire l'URL de base du chatbot depuis l'URL du script
    const scriptUrl = new URL(currentScript.src);
    const chatbotUrl = scriptUrl.origin;

    // Extraire les paramètres de l'URL du script
    const params = new URLSearchParams(scriptUrl.search);
    
    // Configuration depuis les paramètres d'URL
    const config = {
      chatbotUrl: params.get('chatbotUrl') || chatbotUrl,
      position: params.get('position') || 'bottom-right',
      buttonColor: params.get('buttonColor') || '#6366f1',
      buttonSize: params.get('buttonSize') || 'large',
    };

    // Vérifier si un attribut data-* existe sur le script
    if (currentScript.dataset.chatbotUrl) {
      config.chatbotUrl = currentScript.dataset.chatbotUrl;
    }
    if (currentScript.dataset.position) {
      config.position = currentScript.dataset.position;
    }
    if (currentScript.dataset.buttonColor) {
      config.buttonColor = currentScript.dataset.buttonColor;
    }
    if (currentScript.dataset.buttonSize) {
      config.buttonSize = currentScript.dataset.buttonSize;
    }

    // Auto-initialiser si l'attribut data-auto-init existe ou si des paramètres sont présents
    const hasParams = params.toString().length > 0;
    const hasDataAttrs = Object.keys(currentScript.dataset).length > 0;
    const autoInitAttr = currentScript.getAttribute('data-auto-init');

    if (hasParams || hasDataAttrs || autoInitAttr !== 'false') {
      // Attendre que le DOM soit prêt
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
          init(config);
        });
      } else {
        // DOM déjà prêt
        init(config);
      }
    }
  })();
})();

