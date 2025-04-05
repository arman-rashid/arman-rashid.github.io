// JavaScript for enhanced functionality on arman-rashid.github.io
document.addEventListener('DOMContentLoaded', function() {
    // Add scroll progress indicator
    const scrollProgressElement = document.createElement('div');
    scrollProgressElement.className = 'scroll-progress';
    document.body.prepend(scrollProgressElement);

    // Update scroll progress indicator
    window.addEventListener('scroll', function() {
        const totalHeight = document.body.scrollHeight - window.innerHeight;
        const progress = (window.pageYOffset / totalHeight) * 100;
        scrollProgressElement.style.width = progress + '%';
    });

    // Add animation classes to elements when they come into view
    const fadeElements = document.querySelectorAll('h1, h2, h3, .u-container-style, .u-image-1, blockquote');
    fadeElements.forEach(element => {
        element.classList.add('fade-element');
    });

    // Create intersection observer for fade-in animations
    const fadeObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                if (entry.target.tagName === 'H1') {
                    entry.target.classList.add('animate');
                }
                fadeObserver.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1
    });

    // Observe all fade elements
    fadeElements.forEach(element => {
        fadeObserver.observe(element);
    });

    // Add animation to social icons
    const socialIcons = document.querySelector('.u-social-icons');
    if (socialIcons) {
        const socialObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    socialIcons.classList.add('animate');
                    socialObserver.unobserve(entry.target);
                }
            });
        }, {
            threshold: 0.5
        });
        socialObserver.observe(socialIcons);
    }

    // Add animation to repeater items
    const repeaters = document.querySelectorAll('.u-repeater');
    repeaters.forEach(repeater => {
        const repeaterObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    repeater.classList.add('animate');
                    repeaterObserver.unobserve(entry.target);
                }
            });
        }, {
            threshold: 0.1
        });
        repeaterObserver.observe(repeater);
    });

    // Add image reveal animation
    const images = document.querySelectorAll('.u-image-1');
    images.forEach(image => {
        const parent = image.parentElement;
        const wrapper = document.createElement('div');
        wrapper.className = 'image-reveal';
        parent.insertBefore(wrapper, image);
        wrapper.appendChild(image);
        
        const imageObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    wrapper.classList.add('animate');
                    imageObserver.unobserve(entry.target);
                }
            });
        }, {
            threshold: 0.5
        });
        imageObserver.observe(wrapper);
    });

    // Add 3D tilt effect to cards
    const cards = document.querySelectorAll('.u-container-style');
    cards.forEach(card => {
        card.classList.add('tilt-card');
        const content = card.querySelector('.u-container-layout');
        if (content) {
            content.classList.add('tilt-card-content');
        }
        
        card.addEventListener('mousemove', function(e) {
            if (window.innerWidth <= 768) return; // Disable on mobile
            
            const rect = this.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            const xRotation = ((y - rect.height / 2) / rect.height) * 10;
            const yRotation = ((x - rect.width / 2) / rect.width) * -10;
            
            this.style.transform = `perspective(1000px) rotateX(${xRotation}deg) rotateY(${yRotation}deg)`;
        });
        
        card.addEventListener('mouseout', function() {
            this.style.transform = 'perspective(1000px) rotateX(0) rotateY(0)';
        });
    });

    // Add active class to current navigation link
    const navLinks = document.querySelectorAll('.u-btn-1, .u-btn-2, .u-btn-3, .u-btn-4, .u-btn-5');
    const currentPage = window.location.pathname.split('/').pop();
    
    navLinks.forEach(link => {
        const href = link.getAttribute('data-href');
        if (href === currentPage || (currentPage === '' && href === './')) {
            link.classList.add('active');
        }
    });

    // Create particles for hero section
    const heroSection = document.querySelector('.u-section-1');
    if (heroSection) {
        const particlesContainer = document.createElement('div');
        particlesContainer.className = 'particles-container';
        heroSection.prepend(particlesContainer);
        
        const particleCount = 30;
        for (let i = 0; i < particleCount; i++) {
            const particle = document.createElement('div');
            particle.className = 'particle';
            
            // Random size between 2-6px
            const size = Math.random() * 4 + 2;
            particle.style.width = `${size}px`;
            particle.style.height = `${size}px`;
            
            // Random position
            particle.style.left = `${Math.random() * 100}%`;
            particle.style.top = `${Math.random() * 100}%`;
            
            // Random opacity
            particle.style.opacity = Math.random() * 0.5 + 0.1;
            
            // Random animation
            const duration = Math.random() * 20 + 10;
            particle.style.animation = `float ${duration}s ease-in-out infinite`;
            particle.style.animationDelay = `${Math.random() * 5}s`;
            
            particlesContainer.appendChild(particle);
        }
    }

    // Add typing animation to subtitle
    const subtitle = document.querySelector('.u-text-2');
    if (subtitle) {
        subtitle.classList.add('typing-animation');
    }

    // Add gradient background to footer
    const footer = document.querySelector('.u-footer');
    if (footer) {
        footer.classList.add('gradient-bg');
    }

    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                window.scrollTo({
                    top: targetElement.offsetTop - 70,
                    behavior: 'smooth'
                });
            }
        });
    });
});
