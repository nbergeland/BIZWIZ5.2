# BizWiz: Intelligent Location Analytics Dashboard

A comprehensive franchise location intelligence platform that provides data-driven insights for optimal site selection with advanced cannibalization protection algorithms.

## Overview

BizWiz is an enterprise-grade location analytics dashboard designed specifically for franchise development teams. The platform integrates real-time market data, competitor intelligence, and demographic analysis to identify optimal franchise locations while protecting existing investments from revenue cannibalization.

## Key Features

### Market Intelligence
- **Real-time Competitor Mapping**: Live competitor location data via Google Places API
- **Demographic Analysis**: Census Bureau integration for accurate population and income data
- **Market Research Integration**: Comprehensive rental market and property value analysis
- **Geographic Optimization**: Advanced spatial analysis for site selection

### Franchise Protection
- **Cannibalization Risk Assessment**: Distance-based analysis to prevent franchise conflicts
- **Revenue Impact Modeling**: Quantitative assessment of potential revenue impact (up to 80% reduction modeling)
- **Trade Area Protection**: Automated 3.5-mile protection zone analysis
- **Risk Categorization**: Five-tier risk assessment (Critical, High, Moderate, Low, Minimal)
- **Safe Opportunity Identification**: Automated filtering for franchise-safe locations

### Technical Infrastructure
- **Smart Caching System**: 24-hour data persistence with automatic expiry
- **API Rate Limiting**: Optimized API usage with intelligent caching
- **Real-time Data Processing**: Asynchronous data loading with progress tracking
- **Secure Credential Management**: Environment variable and config file support

### Analytics and Visualization
- **Interactive Maps**: Plotly-powered geographic visualizations
- **Revenue Opportunity Analysis**: Comprehensive financial modeling
- **Market Insights Dashboard**: Strategic recommendations and risk mitigation
- **Competitive Intelligence**: Multi-competitor analysis and positioning

## Technical Requirements

### Python Dependencies
```
pandas >= 1.3.0
plotly >= 5.0.0
dash >= 2.0.0
dash-bootstrap-components >= 1.0.0
numpy >= 1.20.0
requests >= 2.25.0
```

### External APIs
- **Google Places API**: Competitor and existing franchise location data
- **U.S. Census Bureau API**: Demographic and economic data
- **Market Research Data**: Integrated rental and property market estimates

### System Requirements
- Python 3.8 or higher
- Minimum 4GB RAM (8GB recommended for large datasets)
- Internet connectivity for API access
- 500MB disk space for cache storage

## Installation

### 1. Clone Repository
```bash
git clone https://github.com/your-organization/bizwiz-dashboard.git
cd bizwiz-dashboard
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure City Database (Optional)
```bash
python generate_usa_cities.py
```

## API Configuration

### Method 1: Environment Variables (Recommended)
```bash
export CENSUS_API_KEY="your_census_api_key_here"
export GOOGLE_PLACES_API_KEY="your_google_places_api_key_here"
```

### Method 2: Configuration File
Create `config/api_keys.json`:
```json
{
  "census_api_key": "your_census_api_key_here",
  "google_places_api_key": "your_google_places_api_key_here"
}
```

### API Key Acquisition

#### Google Places API
1. Visit [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select a project
3. Enable the Places API
4. Create an API key credential
5. Restrict the key to Places API for security

#### U.S. Census API
1. Visit [Census API Key Signup](https://api.census.gov/data/key_signup.html)
2. Complete the registration form
3. Receive API key via email

## Usage

### Starting the Application
```bash
python D52.py
```

The dashboard will be available at `http://127.0.0.1:8051` (or next available port).

### Core Workflow

1. **City Selection**: Choose from comprehensive U.S. city database
2. **Data Loading**: Automatic fresh data collection or cache retrieval
3. **Market Analysis**: Review competitor landscape and demographic data
4. **Franchise Protection**: Analyze cannibalization risks and safe zones
5. **Opportunity Assessment**: Identify optimal franchise-safe locations
6. **Strategic Planning**: Export insights for franchise development decisions

### Navigation Tabs

#### Live Competitor Map
- Interactive geographic visualization of all competitors
- Existing franchise locations with protection zones
- Revenue potential heat mapping
- Real-time data source indicators

#### Real-Time Market Data
- Demographic and economic analytics
- Cannibalization-adjusted revenue projections
- Market penetration analysis
- Cache status and data freshness indicators

#### Revenue Opportunities
- Franchise-safe location rankings
- Risk-adjusted revenue projections
- Distance-based safety analysis
- Moderate-risk evaluation opportunities

#### API Intelligence
- Data quality metrics and source verification
- Franchise protection model performance
- Cache management and optimization
- System status and connectivity monitoring

#### Market Insights
- Strategic market analysis and recommendations
- Competitive positioning insights
- Risk mitigation strategies
- Franchise development roadmap

## Security Considerations

### API Key Management
- Never commit API keys to version control
- Use environment variables in production
- Implement key rotation policies
- Monitor API usage and costs

### Data Protection
- All franchise location data is processed locally
- No sensitive business data transmitted to third parties
- Smart caching includes automatic expiry
- Secure file permissions on cache directory

### Access Control
- Dashboard runs on localhost by default
- Configure firewall rules for network access
- Implement authentication for production deployment

## Cache Management

### Automatic Features
- 24-hour cache expiry with automatic refresh
- Intelligent cache validation and cleanup
- Compressed data storage with metadata tracking
- Corrupted cache detection and recovery

### Manual Operations
- Force refresh for immediate data updates
- Cache statistics and performance monitoring
- Selective cache clearing by city
- Cache directory management and optimization

## Troubleshooting

### Common Issues

#### API Connection Failures
```
Solution: Verify API keys are correctly configured and valid
Check: Network connectivity and firewall settings
Verify: API quota limits and billing status
```

#### Cache Directory Permissions
```
Solution: Ensure write permissions on cache directory
Command: chmod 755 cache/
Verify: Disk space availability
```

#### Missing City Configuration
```
Solution: Run python generate_usa_cities.py
Verify: city_config.py file exists
Check: CityConfigManager import success
```

#### Memory Issues with Large Datasets
```
Solution: Increase system memory allocation
Alternative: Enable selective data loading
Configure: Reduce concurrent API calls
```

### Performance Optimization

#### Large Metropolitan Areas
- Implement data sampling for initial analysis
- Use progressive loading for detailed examination
- Configure cache prewarming for frequently accessed cities

#### API Rate Limiting
- Monitor API usage in Google Cloud Console
- Implement exponential backoff for rate-limited requests
- Configure batch processing for multiple cities

## Architecture Overview

### Data Flow
1. **Input Layer**: City selection and user preferences
2. **API Integration Layer**: Google Places, Census, and market data APIs
3. **Processing Layer**: Cannibalization analysis and risk assessment
4. **Caching Layer**: Smart persistence and retrieval optimization
5. **Visualization Layer**: Interactive maps and analytics dashboards
6. **Output Layer**: Strategic insights and franchise recommendations

### Core Components

#### DataCacheManager
- Persistent storage with metadata tracking
- Automatic expiry and cleanup processes
- Serialization handling for complex objects
- Performance monitoring and optimization

#### Franchise Protection Engine
- Distance-based cannibalization risk calculation
- Revenue impact modeling with industry benchmarks
- Trade area analysis and protection zones
- Risk categorization and recommendation generation

#### Market Intelligence System
- Multi-source data integration and validation
- Real-time competitive landscape analysis
- Demographic profiling and economic indicators
- Geographic optimization algorithms

## Development and Deployment

### Development Environment Setup
```bash
# Create virtual environment
python -m venv bizwiz_env
source bizwiz_env/bin/activate  # Linux/Mac
bizwiz_env\Scripts\activate     # Windows

# Install development dependencies
pip install -r requirements-dev.txt

# Run in development mode
python bizwiz_dashboard.py
```

### Production Deployment Considerations
- Configure robust authentication and authorization
- Implement HTTPS encryption for web traffic
- Set up automated backup for cache and configuration
- Monitor API usage and implement cost controls
- Configure load balancing for high availability

### Environment Configuration
- Separate API keys for development and production
- Configure different cache expiry policies by environment
- Implement environment-specific logging levels
- Set up monitoring and alerting for production systems

## Support and Maintenance

### Regular Maintenance Tasks
- Monitor API key expiry and renewal schedules
- Review and update competitor search algorithms
- Validate demographic data accuracy and sources
- Performance testing with representative datasets

### Monitoring Recommendations
- API response times and error rates
- Cache hit ratios and storage utilization
- User session analytics and feature usage
- System resource consumption patterns

### Update Procedures
- Test API changes in development environment
- Validate cache compatibility after updates
- Review franchise protection algorithm performance
- Document configuration changes and deployment notes

## License

This software is proprietary and confidential. Unauthorized copying, distribution, or modification is strictly prohibited.

## Contact

For technical support, feature requests, or deployment assistance, contact the development team through your organization's standard support channels.
