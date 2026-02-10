import { Link } from 'react-router-dom';
import { useConfigContext } from '../../context/ConfigContext.jsx';
import logo from '../../assets/hot-logo-text.svg';
import('@hotosm/hanko-auth');
import '../../styles/login.css';

function LoginPage() {
  const { config } = useConfigContext();

  const redirectUrl = config?.FRONTEND_URL || window.location.origin;

  return (
    <div className="login-page">
      <div className="login__panel">
        <h1 className="login__title">ChatMap</h1>
        <p className="login__subtitle">Sign in to your account</p>
        <div className="login__form">
          <hotosm-auth
            hanko-url={config?.HANKO_API_URL}
            show-profile="true"
            redirect-after-login={redirectUrl}
            redirect-after-logout={redirectUrl}
          />
        </div>
        <div className="login__back">
          <Link to="/">Back to home</Link>
        </div>
        <div className="login__logo">
          <img src={logo} alt="HOT logo" />
        </div>
      </div>
    </div>
  );
}

export default LoginPage;
