# app/core/insights.py
import openai  # or your preferred LLM

async def generate_insights(monthly_summary: dict) -> str:
    """Generate AI insights from time tracking data."""
    
    prompt = f"""
    Analyze this time tracking data and provide insights:
    
    Month: {monthly_summary['year']}-{monthly_summary['month']:02d}
    Total tracked time: {sum(monthly_summary['app_totals'].values()) / (1000*60*60):.1f} hours
    
    Top applications:
    {chr(10).join(f"- {app}: {ms/(1000*60*60):.1f}h" for app, ms in 
                  sorted(monthly_summary['app_totals'].items(), key=lambda x: x[1], reverse=True)[:10])}
    
    Provide:
    1. Productivity insights
    2. Time distribution analysis
    3. Recommendations for improvement
    """
    
    response = await openai.ChatCompletion.acreate(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500
    )
    
    return response.choices[0].message.content