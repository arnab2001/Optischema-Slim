import type { Metadata } from 'next'

export const metadata: Metadata = {
    metadataBase: new URL('https://arnab2001.github.io/Optischema-Slim/'),
    title: {
        default: 'OptiSchema Slim - Local-First PostgreSQL Doctor',
        template: '%s | OptiSchema Slim'
    },
    description: 'The local-first AI doctor for PostgreSQL. Monitor performance, verify indexes with HypoPG, and optimize queries using local LLMs without data egress.',
    keywords: [
        'PostgreSQL',
        'Database Optimization',
        'HypoPG',
        'Local LLM',
        'SQL Tuning',
        'Database Performance',
        'Ollama',
        'Next.js',
        'Postgres Analysis'
    ],
    authors: [{ name: 'Arnab Chatterjee' }],
    openGraph: {
        title: 'OptiSchema Slim - Local-First PostgreSQL Doctor',
        description: 'Optimize PostgreSQL performance locally. Verify indexes before production.',
        url: 'https://arnab2001.github.io/Optischema-Slim/landing',
        siteName: 'OptiSchema Slim',
        images: [
            {
                url: '/image.png',
                width: 1200,
                height: 630,
                alt: 'OptiSchema Slim Dashboard',
            },
        ],
        locale: 'en_US',
        type: 'website',
    },
    twitter: {
        card: 'summary_large_image',
        title: 'OptiSchema Slim - Local-First PostgreSQL Doctor',
        description: 'Optimize PostgreSQL performance locally. Verify indexes before production.',
        images: ['/image.png'],
    },
    robots: {
        index: true,
        follow: true,
        googleBot: {
            index: true,
            follow: true,
            'max-video-preview': -1,
            'max-image-preview': 'large',
            'max-snippet': -1,
        },
    },
}

export default function LandingLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <>
            <script
                type="application/ld+json"
                dangerouslySetInnerHTML={{
                    __html: JSON.stringify({
                        '@context': 'https://schema.org',
                        '@type': 'SoftwareApplication',
                        name: 'OptiSchema Slim',
                        applicationCategory: 'DeveloperApplication',
                        operatingSystem: 'Any',
                        offers: {
                            '@type': 'Offer',
                            price: '0',
                            priceCurrency: 'USD',
                        },
                        description: 'Local-first PostgreSQL performance optimization tool with AI analysis and HypoPG verification.',
                        featureList: [
                            'Real-time Monitoring',
                            'AI Query Analysis',
                            'HypoPG Index Verification',
                            'Local-First Privacy',
                            'Zero Config'
                        ],
                        author: {
                            '@type': 'Person',
                            name: 'Arnab Chatterjee'
                        }
                    }),
                }}
            />
            {children}
        </>
    )
}
