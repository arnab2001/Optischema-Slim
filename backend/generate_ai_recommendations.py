#!/usr/bin/env python3
"""
Generate real AI-powered recommendations using the actual analysis pipeline.
This script connects to your database, analyzes real queries, and generates recommendations using AI.
"""

import asyncio
import os
import logging
from analysis.pipeline import run_analysis_pipeline
from recommendations_db import RecommendationsDB

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def generate_real_ai_recommendations():
    """Generate real AI recommendations from actual query analysis."""
    
    print("🤖 Generating REAL AI recommendations from query analysis...")
    print("📊 This will:")
    print("   1. Connect to your database")
    print("   2. Analyze actual query performance metrics")
    print("   3. Use AI (Gemini/DeepSeek) to generate recommendations")
    print("   4. Store unique, non-duplicate recommendations")
    print()
    
    try:
        # Set API keys for AI generation
        os.environ['GEMINI_API_KEY'] = 'AIzaSyCfY_KxPVsmlBAxmGakJ6B89g1h-jwf2cE'
        os.environ['DEEPSEEK_API_KEY'] = 'sk-e4022e1036d140e7b5887aa3461f1878'
        os.environ['LLM_PROVIDER'] = 'gemini'
        
        print("🔗 Running analysis pipeline...")
        
        # Run the actual analysis pipeline
        results = await run_analysis_pipeline()
        
        if not results:
            print("❌ Analysis pipeline returned no results")
            print("💡 This might be because:")
            print("   - Database connection issues")
            print("   - No query metrics available")
            print("   - pg_stat_statements not enabled")
            return 0
        
        # Get the AI-generated recommendations
        recommendations = results.get('recommendations', [])
        
        if not recommendations:
            print("❌ No recommendations generated")
            print("💡 Try running some queries on your connected database first")
            return 0
        
        print(f"🎯 AI Generated {len(recommendations)} recommendations")
        
        # Store the AI recommendations in the database
        stored_count = 0
        for rec in recommendations:
            try:
                # Convert Pydantic model to dict if needed
                if hasattr(rec, 'model_dump'):
                    rec_dict = rec.model_dump()
                elif hasattr(rec, 'dict'):
                    rec_dict = rec.dict()
                else:
                    rec_dict = rec
                
                # Store in SQLite
                rec_id = RecommendationsDB.store_recommendation(rec_dict)
                
                # Show what was generated
                title = rec_dict.get('title', 'Unknown')
                rec_type = rec_dict.get('recommendation_type', 'unknown')
                has_sql = '🔧 Executable' if rec_dict.get('sql_fix') else '📋 Advisory'
                confidence = rec_dict.get('confidence_score', 'N/A')
                improvement = rec_dict.get('estimated_improvement_percent', 'N/A')
                
                print(f"✅ {has_sql}: {title}")
                print(f"   Type: {rec_type} | Confidence: {confidence}% | Improvement: {improvement}%")
                
                if rec_dict.get('sql_fix'):
                    sql_preview = rec_dict['sql_fix'][:60] + "..." if len(rec_dict['sql_fix']) > 60 else rec_dict['sql_fix']
                    print(f"   SQL: {sql_preview}")
                print()
                
                stored_count += 1
                
            except Exception as e:
                logger.error(f"Failed to store recommendation: {e}")
        
        print(f"🎉 Successfully stored {stored_count} AI-generated recommendations!")
        print("✅ These are real recommendations based on your actual query patterns")
        
        # Show summary
        analysis_summary = results.get('core_analysis', {})
        queries_analyzed = results.get('hot_queries_analyzed', 0)
        total_queries = results.get('total_queries_analyzed', 0)
        
        print(f"\n📈 Analysis Summary:")
        print(f"   Total queries analyzed: {total_queries}")
        print(f"   Hot queries identified: {queries_analyzed}")
        print(f"   AI recommendations generated: {stored_count}")
        
        return stored_count
        
    except Exception as e:
        logger.error(f"Failed to generate AI recommendations: {e}")
        print(f"❌ Error: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Ensure your database is connected")
        print("   2. Check that pg_stat_statements is enabled")
        print("   3. Run some queries to generate metrics")
        print("   4. Verify API keys are working")
        return 0

async def clear_old_recommendations():
    """Clear old recommendations to start fresh."""
    try:
        # Get current count
        current_recs = RecommendationsDB.list_recommendations(limit=1000)
        if current_recs:
            print(f"🧹 Found {len(current_recs)} existing recommendations")
            
            # Ask user if they want to clear
            response = input("Clear existing recommendations? (y/N): ").strip().lower()
            if response in ['y', 'yes']:
                # Simple way: delete the database file
                import os
                from pathlib import Path
                db_path = Path("/tmp/optischema_recommendations.db")
                if db_path.exists():
                    os.remove(db_path)
                    print("✅ Cleared all existing recommendations")
                else:
                    print("ℹ️  No database file found")
        else:
            print("ℹ️  No existing recommendations found")
    except Exception as e:
        print(f"Warning: Could not check existing recommendations: {e}")

if __name__ == "__main__":
    print("🚀 AI Recommendation Generator")
    print("===============================")
    
    # Optionally clear old recommendations
    asyncio.run(clear_old_recommendations())
    
    # Generate new AI recommendations
    count = asyncio.run(generate_real_ai_recommendations())
    
    if count > 0:
        print(f"\n🎯 SUCCESS!")
        print(f"Generated {count} real AI recommendations")
        print("🌐 Refresh your frontend to see the new recommendations!")
    else:
        print("\n❌ No recommendations generated")
        print("💡 Check database connection and query metrics") 