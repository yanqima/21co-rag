"""
Profiling utilities for analyzing performance from logs.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict
import statistics


def parse_timestamp(timestamp_str: str) -> datetime:
    """Parse ISO format timestamp."""
    try:
        # Handle both formats with and without microseconds
        if '.' in timestamp_str:
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        else:
            return datetime.fromisoformat(timestamp_str.replace('Z', '') + '+00:00')
    except:
        return datetime.now()


def analyze_request_logs(logs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze logs for a single request (by correlation ID)."""
    if not logs:
        return {}
    
    # Sort logs by timestamp
    sorted_logs = sorted(logs, key=lambda x: parse_timestamp(x.get('timestamp', '')))
    
    # Find request start and end
    request_start = None
    request_end = None
    phases = {}
    
    for log in sorted_logs:
        event = log.get('event', '')
        timestamp = parse_timestamp(log.get('timestamp', ''))
        
        if event == 'request_started':
            request_start = timestamp
        elif event == 'request_completed':
            request_end = timestamp
        
        # Track phase starts and ends
        if event.endswith('_started'):
            phase_name = event.replace('_started', '')
            phases[phase_name] = {'start': timestamp}
        elif event.endswith('_completed'):
            phase_name = event.replace('_completed', '')
            if phase_name in phases:
                phases[phase_name]['end'] = timestamp
    
    # Calculate phase durations
    phase_durations = {}
    for phase, times in phases.items():
        if 'start' in times and 'end' in times:
            duration = (times['end'] - times['start']).total_seconds()
            phase_durations[phase] = duration
    
    # Calculate total duration
    total_duration = None
    if request_start and request_end:
        total_duration = (request_end - request_start).total_seconds()
    
    return {
        'correlation_id': logs[0].get('correlation_id'),
        'total_duration': total_duration,
        'phase_durations': phase_durations,
        'start_time': request_start,
        'end_time': request_end,
        'log_count': len(logs)
    }


def aggregate_performance_stats(all_logs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate performance statistics from multiple requests."""
    # Group logs by correlation ID
    requests_by_correlation = defaultdict(list)
    for log in all_logs:
        corr_id = log.get('correlation_id')
        if corr_id and corr_id != 'none':
            requests_by_correlation[corr_id].append(log)
    
    # Analyze each request
    request_analyses = []
    for corr_id, logs in requests_by_correlation.items():
        analysis = analyze_request_logs(logs)
        if analysis.get('total_duration'):
            request_analyses.append(analysis)
    
    if not request_analyses:
        return {
            'total_requests': 0,
            'phase_stats': {},
            'duration_stats': {}
        }
    
    # Aggregate phase statistics
    phase_durations_all = defaultdict(list)
    total_durations = []
    
    for analysis in request_analyses:
        if analysis['total_duration']:
            total_durations.append(analysis['total_duration'])
        
        for phase, duration in analysis.get('phase_durations', {}).items():
            phase_durations_all[phase].append(duration)
    
    # Calculate statistics for each phase
    phase_stats = {}
    for phase, durations in phase_durations_all.items():
        if durations:
            phase_stats[phase] = {
                'avg': statistics.mean(durations),
                'min': min(durations),
                'max': max(durations),
                'p50': statistics.median(durations),
                'p95': statistics.quantiles(durations, n=20)[18] if len(durations) > 1 else durations[0],
                'count': len(durations)
            }
    
    # Calculate overall statistics
    duration_stats = {}
    if total_durations:
        duration_stats = {
            'avg': statistics.mean(total_durations),
            'min': min(total_durations),
            'max': max(total_durations),
            'p50': statistics.median(total_durations),
            'p95': statistics.quantiles(total_durations, n=20)[18] if len(total_durations) > 1 else total_durations[0],
            'count': len(total_durations)
        }
    
    return {
        'total_requests': len(request_analyses),
        'phase_stats': phase_stats,
        'duration_stats': duration_stats,
        'recent_requests': request_analyses[-10:]  # Last 10 requests
    }


def identify_bottlenecks(phase_stats: Dict[str, Dict[str, float]]) -> List[Dict[str, Any]]:
    """Identify performance bottlenecks from phase statistics."""
    bottlenecks = []
    
    # Calculate total average time
    total_avg = sum(stats['avg'] for stats in phase_stats.values())
    
    for phase, stats in phase_stats.items():
        percentage = (stats['avg'] / total_avg * 100) if total_avg > 0 else 0
        
        bottlenecks.append({
            'phase': phase,
            'avg_duration': stats['avg'],
            'percentage': percentage,
            'max_duration': stats['max']
        })
    
    # Sort by average duration descending
    bottlenecks.sort(key=lambda x: x['avg_duration'], reverse=True)
    
    return bottlenecks