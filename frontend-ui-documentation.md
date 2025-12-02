# OptiSchema Frontend/UI Documentation

## 📱 Application Structure

### **Framework & Technology Stack**
- **Framework**: Next.js 15.4.1 with App Router
- **UI Library**: React 19.1.0 with TypeScript 4.9.5
- **Styling**: Tailwind CSS 3.3.3 with custom design system
- **Icons**: Lucide React 0.525.0
- **Charts**: Recharts 3.1.0 for data visualization
- **State Management**: SWR 2.2.4 for data fetching and caching
- **UI Components**: Radix UI primitives for accessibility

---

## 🏠 Pages & Routes

### **1. Landing Page (`/`)**
**File**: `frontend/app/page.tsx`

**Purpose**: Marketing and product introduction page

**Sections**:
- **Navbar**: Logo, navigation links, CTA buttons
- **Hero**: Main value proposition and primary CTA
- **Value Snapshot**: Key benefits and features overview
- **Problem/Solution**: Pain points and how OptiSchema solves them
- **Live Preview Demo**: Interactive product demonstration
- **Feature Pillars**: Core functionality highlights
- **How It Works**: Step-by-step process explanation
- **Deep Dive**: Technical details and capabilities
- **Social Proof**: Testimonials and case studies
- **Supported Databases**: Database compatibility information
- **Security**: Security features and compliance
- **FAQ**: Frequently asked questions
- **Final CTA**: Call-to-action for signup/trial
- **Footer**: Links, legal, contact information

**Key Components**:
- `Navbar`: Top navigation with logo and CTAs
- `Hero`: Main landing section with value proposition
- `ValueSnapshot`: Quick benefits overview
- `ProblemSolution`: Problem/solution narrative
- `LivePreviewDemo`: Interactive product demo
- `FeaturePillars`: Core features showcase
- `HowItWorks`: Process explanation
- `DeepDive`: Technical capabilities
- `SocialProof`: Customer testimonials
- `SupportedDatabases`: Database support matrix
- `Security`: Security and compliance info
- `FAQ`: Frequently asked questions
- `FinalCTA`: Signup/trial call-to-action
- `Footer`: Site footer with links

---

### **2. Dashboard Page (`/dashboard`)**
**File**: `frontend/app/dashboard/page.tsx`

**Purpose**: Main application interface for database optimization

**Layout Structure**:
- **Header Section**: Connection status, database switcher, dark mode toggle
- **Navigation Tabs**: 7 main sections (Overview, Optimizations, Analytics, Audit, Baselines, Indexes, Apply)
- **Main Content Area**: Tab-specific content and components

**Tab Structure**:

#### **Overview Tab** (Default)
- **Welcome Banner**: Connection status and quick actions
- **KPI Banner**: Key performance indicators
- **Metrics Cards**: Performance metrics display
- **Query Table**: Top queries with performance data
- **Performance Charts**: Visual performance trends
- **System Status**: Database and service health

#### **Optimizations Tab** (Suggestions)
- **Recommendation Cards**: AI-generated optimization suggestions
- **Filter Controls**: Filter by type, risk level, confidence
- **Apply/Rollback Actions**: Apply or rollback recommendations
- **Benchmark Modal**: Test optimizations in sandbox

#### **Analytics Tab**
- **Historical Data**: Performance trends over time
- **Latency Trend Chart**: Query performance visualization
- **Query Heat Map**: Query performance patterns
- **Export Manager**: Data export functionality

#### **Audit Tab**
- **Audit Logs**: Complete change history
- **Filter Controls**: Date range, action type filters
- **Summary Statistics**: Audit activity overview
- **Export Options**: CSV/JSON export

#### **Connection Baselines Tab**
- **Connection Management**: Database connection configuration
- **Baseline Measurement**: Performance baseline establishment
- **Connection History**: Previous connection records
- **Latency Testing**: Connection performance testing

#### **Index Advisor Tab**
- **Index Recommendations**: Database index suggestions
- **Index Analysis**: Current index usage analysis
- **Sandbox Testing**: Safe index testing environment
- **Performance Impact**: Index optimization results

#### **Apply Manager Tab**
- **Applied Changes**: Status of applied optimizations
- **Rollback Management**: Rollback applied changes
- **Change History**: Complete change tracking
- **Status Monitoring**: Real-time operation status

---

## 🧩 Component Library

### **Core UI Components**

#### **1. MetricsCard**
**File**: `frontend/components/MetricsCard.tsx`
**Purpose**: Display key performance metrics
**Props**:
- `title`: Metric title
- `value`: Metric value
- `change`: Change percentage
- `trend`: Trend direction (up/down)
- `icon`: Icon component

#### **2. QueryTable**
**File**: `frontend/components/QueryTable.tsx`
**Purpose**: Display query performance data in table format
**Features**:
- Sortable columns
- Pagination
- Query details on click
- Performance metrics display
- Filtering capabilities

#### **3. RecommendationCard**
**File**: `frontend/components/RecommendationCard.tsx`
**Purpose**: Display AI-generated optimization recommendations
**Features**:
- Recommendation details
- Confidence score
- Risk level indicator
- Apply/rollback actions
- SQL fix preview

#### **4. PerformanceChart**
**File**: `frontend/components/PerformanceChart.tsx`
**Purpose**: Visualize performance trends
**Features**:
- Time-series data
- Multiple metrics
- Interactive tooltips
- Responsive design

### **Navigation & Layout Components**

#### **5. DatabaseSwitcher**
**File**: `frontend/components/DatabaseSwitcher.tsx`
**Purpose**: Switch between database connections
**Features**:
- Connection management
- Connection testing
- Connection history
- pg_stat_statements configuration

#### **6. ConnectionWizard**
**File**: `frontend/components/ConnectionWizard.tsx`
**Purpose**: Guided database connection setup
**Features**:
- Step-by-step connection setup
- Connection validation
- SSL configuration
- Connection testing

#### **7. DarkModeToggle**
**File**: `frontend/components/DarkModeToggle.tsx`
**Purpose**: Toggle between light and dark themes
**Features**:
- Theme persistence
- System preference detection
- Smooth transitions

### **Data Visualization Components**

#### **8. LatencyTrendChart**
**File**: `frontend/components/LatencyTrendChart.tsx`
**Purpose**: Display query latency trends over time
**Features**:
- Time-series visualization
- Multiple query comparison
- Interactive zoom/pan
- Export capabilities

#### **9. QueryHeatMap**
**File**: `frontend/components/QueryHeatMap.tsx`
**Purpose**: Visualize query performance patterns
**Features**:
- Heat map visualization
- Time-based patterns
- Performance intensity mapping
- Interactive exploration

#### **10. Sparkline**
**File**: `frontend/components/Sparkline.tsx`
**Purpose**: Mini trend charts for quick insights
**Features**:
- Compact visualization
- Trend indicators
- Color-coded performance
- Inline display

### **Modal & Dialog Components**

#### **11. RecommendationModal**
**File**: `frontend/components/RecommendationModal.tsx`
**Purpose**: Detailed recommendation view and actions
**Features**:
- Full recommendation details
- SQL fix preview
- Apply/rollback actions
- Risk assessment
- Performance impact

#### **12. BenchmarkModal**
**File**: `frontend/components/BenchmarkModal.tsx`
**Purpose**: Configure and run performance benchmarks
**Features**:
- Benchmark configuration
- Sandbox testing
- Performance comparison
- Results visualization

#### **13. ExecutionPlanModal**
**File**: `frontend/components/ExecutionPlanModal.tsx`
**Purpose**: Display query execution plans
**Features**:
- Plan visualization
- Cost analysis
- Node details
- Performance metrics

### **Status & Feedback Components**

#### **14. SystemStatus**
**File**: `frontend/components/SystemStatus.tsx`
**Purpose**: Display system health and status
**Features**:
- Service status indicators
- Health check results
- Performance metrics
- Error notifications

#### **15. LiveIndicator**
**File**: `frontend/components/LiveIndicator.tsx`
**Purpose**: Show real-time data updates
**Features**:
- Live data indicator
- Update timestamps
- Connection status
- Data freshness

#### **16. ProgressIndicator**
**File**: `frontend/components/ProgressIndicator.tsx`
**Purpose**: Show operation progress
**Features**:
- Progress bars
- Status messages
- Completion indicators
- Error handling

### **Specialized Tab Components**

#### **17. AuditTab**
**File**: `frontend/components/AuditTab.tsx`
**Purpose**: Complete audit log management
**Features**:
- Audit log display
- Filtering and search
- Export functionality
- Summary statistics
- Action type filtering

#### **18. IndexAdvisorTab**
**File**: `frontend/components/IndexAdvisorTab.tsx`
**Purpose**: Database index optimization
**Features**:
- Index recommendations
- Usage analysis
- Sandbox testing
- Performance impact
- Duplicate detection

#### **19. ConnectionBaselineTab**
**File**: `frontend/components/ConnectionBaselineTab.tsx`
**Purpose**: Connection performance management
**Features**:
- Baseline measurement
- Connection testing
- Performance monitoring
- History tracking

#### **20. ApplyStatusDashboard**
**File**: `frontend/components/ApplyStatusDashboard.tsx`
**Purpose**: Manage applied optimizations
**Features**:
- Applied changes tracking
- Rollback management
- Status monitoring
- Change history

### **Utility Components**

#### **21. QueryFilters**
**File**: `frontend/components/QueryFilters.tsx`
**Purpose**: Filter and search queries
**Features**:
- Multiple filter options
- Search functionality
- Sort controls
- Reset options

#### **22. ExportManager**
**File**: `frontend/components/ExportManager.tsx`
**Purpose**: Export data in various formats
**Features**:
- Multiple export formats
- Data selection
- Export progress
- Download management

#### **23. SkeletonLoader**
**File**: `frontend/components/SkeletonLoader.tsx`
**Purpose**: Loading state placeholders
**Features**:
- Skeleton animations
- Responsive design
- Content placeholders
- Loading states

---

## 🎨 Design System

### **Color Palette**
- **Primary**: Blue (#3B82F6)
- **Secondary**: Green (#10B981)
- **Accent**: Purple (#8B5CF6)
- **Neutral**: Gray scale (#F8FAFC to #0F172A)
- **Success**: Green (#10B981)
- **Warning**: Yellow (#F59E0B)
- **Error**: Red (#EF4444)
- **Info**: Blue (#3B82F6)

### **Typography**
- **Font Family**: Inter (system font stack)
- **Headings**: Font weights 600-700
- **Body**: Font weight 400
- **Code**: JetBrains Mono

### **Spacing System**
- **Base Unit**: 4px
- **Scale**: 4px, 8px, 12px, 16px, 20px, 24px, 32px, 40px, 48px, 64px, 80px, 96px

### **Component Sizes**
- **Small**: 32px height
- **Medium**: 40px height
- **Large**: 48px height
- **Extra Large**: 56px height

---

## 🔄 State Management

### **Local State (useState)**
- Component-specific state
- UI interactions
- Form inputs
- Modal visibility

### **Global State (SWR)**
- API data fetching
- Caching
- Revalidation
- Error handling

### **State Structure**
```typescript
// Dashboard state
const [metrics, setMetrics] = useState<any>(null)
const [suggestions, setSuggestions] = useState<any[]>([])
const [activeTab, setActiveTab] = useState<string>('overview')
const [loading, setLoading] = useState(true)
const [connected, setConnected] = useState<boolean>(false)

// Filter state
const [filters, setFilters] = useState({
  minCalls: 1,
  minTime: 0,
  limit: 25,
  sortBy: 'total_time',
  order: 'desc' as 'asc' | 'desc'
})
```

---

## 🌐 API Integration

### **API Routes (Next.js)**
- `/api/metrics/*` - Query metrics and performance data
- `/api/suggestions/*` - AI recommendations and optimization
- `/api/connection/*` - Database connection management
- `/api/audit/*` - Audit logs and change tracking
- `/api/index-advisor/*` - Index optimization
- `/api/apply/*` - Apply/rollback operations

### **Data Fetching Patterns**
```typescript
// SWR for data fetching
const { data, error, mutate } = useSWR('/api/metrics/raw', fetcher)

// Manual API calls
const fetchData = async () => {
  const response = await fetch('/api/suggestions/latest')
  const data = await response.json()
  setSuggestions(data)
}
```

---

## 📱 Responsive Design

### **Breakpoints**
- **Mobile**: < 640px
- **Tablet**: 640px - 1024px
- **Desktop**: > 1024px

### **Mobile Adaptations**
- Collapsible navigation
- Touch-friendly controls
- Simplified layouts
- Swipe gestures

### **Tablet Adaptations**
- Side-by-side layouts
- Touch interactions
- Optimized spacing
- Flexible grids

---

## ♿ Accessibility Features

### **Keyboard Navigation**
- Tab order management
- Keyboard shortcuts
- Focus indicators
- Escape key handling

### **Screen Reader Support**
- ARIA labels
- Semantic HTML
- Role attributes
- Alt text for images

### **Color Contrast**
- WCAG AA compliance
- High contrast mode
- Color-blind friendly
- Focus indicators

---

## 🚀 Performance Optimizations

### **Code Splitting**
- Dynamic imports
- Lazy loading
- Route-based splitting
- Component-based splitting

### **Caching Strategy**
- SWR caching
- Browser caching
- API response caching
- Static asset caching

### **Bundle Optimization**
- Tree shaking
- Dead code elimination
- Minification
- Compression

---

## 🐛 Known UI Issues

### **Critical Issues**
1. **Too Many Tabs**: 7 tabs create cognitive overload
2. **Mobile Responsiveness**: Poor mobile experience
3. **Loading States**: Inconsistent loading indicators
4. **Error Handling**: Poor error message display

### **Medium Issues**
1. **Dark Mode**: Incomplete dark mode implementation
2. **Accessibility**: Missing ARIA labels
3. **Performance**: Large bundle size
4. **UX Flow**: Confusing navigation patterns

### **Minor Issues**
1. **Typography**: Inconsistent font sizes
2. **Spacing**: Inconsistent spacing
3. **Icons**: Missing icons in some places
4. **Animations**: Jarring transitions

---

## 🔧 Development Guidelines

### **Component Structure**
```typescript
interface ComponentProps {
  // Props definition
}

export default function Component({ prop1, prop2 }: ComponentProps) {
  // Hooks
  const [state, setState] = useState()
  
  // Effects
  useEffect(() => {
    // Side effects
  }, [])
  
  // Event handlers
  const handleClick = () => {
    // Event handling
  }
  
  // Render
  return (
    <div className="component-wrapper">
      {/* JSX content */}
    </div>
  )
}
```

### **Styling Guidelines**
- Use Tailwind CSS classes
- Follow design system tokens
- Use semantic class names
- Maintain consistency

### **State Management**
- Use useState for local state
- Use SWR for server state
- Minimize prop drilling
- Use context for global state

---

*This documentation should be updated as the UI evolves and new components are added.*
