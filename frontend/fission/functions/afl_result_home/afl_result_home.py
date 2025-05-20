import logging
from typing import Dict, Any, List
from flask import current_app
from elasticsearch8 import Elasticsearch

# fission package create --spec --name afl-result-home-pkg \
# --source ./afl_result_home/__init__.py \
# --source ./afl_result_home/afl_result_home.py \
# --source ./afl_result_home/requirements.txt \
# --source ./afl_result_home/build.sh \
# --env python39x --buildcmd './build.sh'

# fission fn create --spec --name afl-result-home \
# --pkg afl-result-home-pkg \
# --env python39x \
# --entrypoint "afl_result_home.main" \
# --specializationtimeout 180 \
# --secret elastic-secret 

# fission route create --spec --name afl-result-home \
# --function afl-result-home \
# --method GET \
# --url /afl/result/home \
# --createingress

# kubectl port-forward service/router -n fission 8080:80

# fission fn log -f --name afl-result-home
# curl -k http://localhost:8080/afl/result/home | jq

def main() -> Dict[str, Any]:
    """Analyse AFL team performance by home/away status (win rates)
    
    Returns:
        JSON response containing:
        - teams_performance: Win rates for each team split by home/away
        - overall_stats: Aggregate home/away win rates
        - team_count: Number of teams analyzed
    """

    # Elasticsearch connection
    with open("/secrets/default/elastic-secret/ES_USERNAME") as f:
        es_username = f.read().strip()

    with open("/secrets/default/elastic-secret/ES_PASSWORD") as f:
        es_password = f.read().strip() 

    es_client = Elasticsearch(
        'https://elasticsearch-master.elastic.svc.cluster.local:9200',
        verify_certs=False,
        ssl_show_warn=False,
        basic_auth=(es_username, es_password)
    )
    
    # Query
    # The query uses aggregations to:
    # 1. Group by team
    # 2. For each team, separate home and away games
    # 3. Count wins in each category
    # 4. Also get overall league-wide home/away stats
    query_body = {
        "size": 0,
        "query": {
            "term": {"completed": True} # Only analyse completed games
        },
        "aggs": {
            # First aggregation level: Group by team
            "teams": {
                "terms": {
                    "field": "team.keyword",
                    "size": 100
                },
                # Nested aggregations for each team
                "aggs": {
                    # Home games sub-aggregation
                    "home_games": {
                        "filter": {"term": {"is_home": True}}, # Only home games
                        "aggs": {
                            "wins": {"filter": {"term": {"result.keyword": "Winner"}}}
                        }
                    },
                    # Away games sub-aggregation
                    "away_games": {
                        "filter": {"term": {"is_home": False}}, # Only away games
                        "aggs": {
                            "wins": {"filter": {"term": {"result.keyword": "Winner"}}}
                        }
                    }
                }
            },
            # Separate aggregation for overall league stats
            "overall_stats": {
                "filters": {
                    "filters": {
                        "home": {"term": {"is_home": True}}, # All home games
                        "away": {"term": {"is_home": False}} # All away games
                    }
                },
                # Win counts for overall home/away
                "aggs": {
                    "wins": {"filter": {"term": {"result.keyword": "Winner"}}}
                }
            }
        }
    }

    current_app.logger.info('Executing AFL home/away performance query')
    
    res = es_client.search(index='afl-scores*', body=query_body)

    # Process results
    # Extract team data from aggregations
    teams_data = res.get('aggregations', {}).get('teams', {}).get('buckets', [])
    # Extract overall stats from aggregations
    overall_data = res.get('aggregations', {}).get('overall_stats', {}).get('buckets', {})
    
    if not teams_data:
        return {'error': 'No team data found'}, 404


    # Process each team's data
    team_performance = []
    for team in teams_data:
        home = team.get('home_games', {})
        away = team.get('away_games', {})
        
        # Extract win counts and total games
        home_wins = home.get('wins', {}).get('doc_count', 0)
        home_games = home.get('doc_count', 0)
        away_wins = away.get('wins', {}).get('doc_count', 0)
        away_games = away.get('doc_count', 0)
        
        # Calculate win rates (handle division by zero)
        home_win_rate = home_wins / home_games if home_games > 0 else 0
        away_win_rate = away_wins / away_games if away_games > 0 else 0
        
        team_performance.append({
            'team': team['key'],
            'home_win_rate': home_win_rate,
            'away_win_rate': away_win_rate,
            'home_games': home_games,
            'away_games': away_games
        })

    # Process overall statistics
    home_games_total = overall_data.get('home', {}).get('doc_count', 0)
    away_games_total = overall_data.get('away', {}).get('doc_count', 0)
    home_wins_total = overall_data.get('home', {}).get('wins', {}).get('doc_count', 0)
    away_wins_total = overall_data.get('away', {}).get('wins', {}).get('doc_count', 0)

    # Calculate overall win rates (handle division by zero)
    overall_home_win_rate = home_wins_total / home_games_total if home_games_total > 0 else 0
    overall_away_win_rate = away_wins_total / away_games_total if away_games_total > 0 else 0

    return {
        'teams_performance': team_performance,
        'overall_stats': {
            'home_win_rate': overall_home_win_rate,
            'away_win_rate': overall_away_win_rate,
            'total_games': home_games_total + away_games_total
        },
        'team_count': len(team_performance)
    }