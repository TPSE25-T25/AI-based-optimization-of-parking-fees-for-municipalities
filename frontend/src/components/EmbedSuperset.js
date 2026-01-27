import {embedDashboard} from '@superset-ui/embedded-sdk';
import axios from 'axios';

const SUPERSET_URL = "http://localhost:8088";
const SUPERSET_CONTAINER_ID = "foo"; // ID of HTML element that will contain the dashboard
const SUPERSET_API_URL = SUPERSET_URL + "/api/v1/security";
const SUPERSET_EMBEDDING_ID = "bar"; // ID of dashboard to be embedded

async function getAccessToken() {
  const credentials = { //temporary, to be replaced w/ backend call
      "password": "admin",
      "provider": "db",
      "refresh": true,
      "username": "admin"
  };

  const headers = {
      "headers": {
        "Content-Type": "application/json"
      }
  };

  await axios.post(SUPERSET_API_URL + '/login', credentials, headers)
  .then(function (response) {
    return({response}['access_token']);
  })
  .error(function (error) {
    setError(true);
    console.error(error);
  });
}

async function fetchGuestTokenFromBackend() {
  const guest_token_body = JSON.stringify({ //to be replaced w/ backend call
    "resources": [
    {
        "type": "dashboard",
        "id": SUPERSET_EMBEDDING_ID
    }
    ],
    "rls": [],
    "user": {
    "username": "",
    "first_name": "",
    "last_name": "",
    }
  });

  const guest_token_headers = {
    "headers": {
    "Content-Type": "application/json",
    "Authorization": '' + access_token
    }
  }

  await axios.post(SUPERSET_API_URL + '/guest_token', guest_token_body, guest_token_headers)
  .then(function(response) {
    return(response.data['token']);
  })
  .error(function(error) {
    console.error(error);
  });
}

function SupersetDashboard() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);



  // Template from superset-ui/embedded-dsk documentation
  embedDashboard({
  id: SUPERSET_EMBEDDING_ID, // given by the Superset embedding UI
  supersetDomain: SUPERSET_URL,
  mountPoint: document.getElementById(SUPERSET_CONTAINER_ID), // any html element that can contain an iframe
  fetchGuestToken: () => fetchGuestTokenFromBackend(),
  dashboardUiConfig: { // dashboard UI config: hideTitle, hideTab, hideChartControls, filters.visible, filters.expanded (optional), urlParams (optional)
      hideTitle: true,
      hideTab: true,
      filters: {
          expanded: true,
      },
      urlParams: {
          foo: 'value1',
          bar: 'value2',
          // ...
      }
  },
    // optional additional iframe sandbox attributes
  iframeSandboxExtras: ['allow-top-navigation', 'allow-popups-to-escape-sandbox'],
  // optional config to enforce a particular referrerPolicy
  referrerPolicy: "same-origin"
  });

  return(
    <div>

    </div>
  );
}