      MODULE SHARED_VARS
      
      REAL*8, PARAMETER :: ZERO  = 0.D0
      REAL*8, PARAMETER :: ONE   = 1.D0
      REAL*8, PARAMETER :: TWO   = 2.D0
      REAL*8, PARAMETER :: THREE = 3.D0
      REAL*8, PARAMETER :: PIE   = 3.1415926535D0
      
                    !=== Laser Properties ===!
      REAL*8, PARAMETER :: VELOCITY   = 800.D-3   ! scan speed
      REAL*8, PARAMETER :: POWER      = 150.D0    ! laser power
      REAL*8, PARAMETER :: RADIUS     = 5.D-5     ! laser radius
      REAL*8, PARAMETER :: ABSORB     = 3.D-1     ! laser absorption ratio
      REAL*8, PARAMETER :: DELTA      = 30.D-6    ! optical penetration depth for laser in powder Yin2016
      REAL*8, PARAMETER :: WIDTH      = 100.D-6   ! Width of a single layer
      REAL*8, PARAMETER :: SMOLL      = 1.D-6     ! Small value for space limits
      REAL*8, PARAMETER :: MIN_INC    = 1.D-8     ! Minimum allowed time increment
      
                    !=== Geometry ===!
      REAL*8, PARAMETER :: STEP           = 0.D0
      REAL*8, PARAMETER :: TIME_SHIFT     = 0.D0
      REAL*8, PARAMETER :: LOCALS         = 10.D0
      REAL*8, PARAMETER :: THICKNESS      = 30.D-6
      REAL*8, PARAMETER :: GLOBAL_LENGTH  = 2.D-3  ! global print length per layer
      REAL*8, PARAMETER :: COOL_TIME      = 1.D0   ! duration of cooldown step
      REAL*8, PARAMETER :: HEAT_TIME      = GLOBAL_LENGTH/VELOCITY
      REAL*8, PARAMETER :: TTLL_TIME      = HEAT_TIME + COOL_TIME   ! total layer time
      
                    !=== Phase Change ===!
      REAL*8, PARAMETER :: MELT_TEMP      = 1.427D+3
      REAL*8, PARAMETER :: PHASE_T_SLD    = 3.D4
      REAL*8, PARAMETER :: PHASE_T_LQD    = 1.3D5

      END MODULE SHARED_VARS

      
      SUBROUTINE DFLUX(FLUX,SOL,KSTEP,KINC,TIME,NOEL,NPT,COORDS,
     1 JLTYP,TEMP,PRESS,SNAME)
      USE SHARED_VARS
      INCLUDE 'ABA_PARAM.INC'
      DIMENSION FLUX(2), TIME(2), COORDS(3)
      CHARACTER*80 SNAME
      REAL*8 x_cur,y_cur,Q,Q0,X0,Y0,
     1 layer_number,layer_time,layer_time_rnd,direction_x
      LOGICAL heated_state
      
      x_cur   = (INT(COORDS(1) * 1.D8 + 0.5D0)) / 1.D8
      y_cur   = (INT(COORDS(2) * 1.D8 + 0.5D0)) / 1.D8
      FLUX(1) = ZERO
      
      CALL LAYER_NO(TIME(2),ONE,layer_number)
      
      layer_time  = TIME(2) + TIME_SHIFT - (layer_number-ONE)*TTLL_TIME    ! current layer time
      layer_time_rnd = FLOAT(INT(layer_time * 1.D8 + 0.5D0)) / 1.D8
      direction_x = (-ONE)**(layer_number-ONE)
      
      IF (direction_x .GT. ZERO) THEN
        IF (COORDS(1) .LT. ZERO - SMOLL .OR.
     1      COORDS(1) .GT. GLOBAL_LENGTH-RADIUS*0.4D0 + SMOLL) THEN
            RETURN
	    END IF
      ELSE
        IF (COORDS(1) .LT. ZERO+RADIUS*0.4D0 - SMOLL .OR.
     1      COORDS(1) .GT. GLOBAL_LENGTH + SMOLL) THEN
            RETURN
	    END IF
      END IF

      ! If it's heating time
      IF (layer_time_rnd.LE.HEAT_TIME) THEN
        ! If we are in +x direction
        IF (direction_x.GT.ZERO) THEN
           X0 = VELOCITY*layer_time_rnd
        ! If -x direction
        ELSE
           X0 = GLOBAL_LENGTH-VELOCITY*layer_time_rnd
        END IF
        Y0=THICKNESS*layer_number
      ELSE
        RETURN
      END IF

      IF (y_cur.LT.Y0+SMOLL .AND. y_cur.GT.Y0-THICKNESS+SMOLL) THEN
        IF (x_cur.LT.X0+RADIUS-SMOLL .AND. x_cur.GT.X0-RADIUS+SMOLL) THEN
            Q0 = SQRT(TWO)*ABSORB*POWER/(SQRT(PIE)*RADIUS*WIDTH*DELTA)
            FLUX(1) = Q0*exp(-TWO*((x_cur-X0)**TWO/RADIUS**TWO))
        END IF 
      END IF 

      RETURN
      END
      
      
      SUBROUTINE FILM(H,SINK,TEMP,KSTEP,KINC,TIME,NOEL,NPT,
     1 COORDS,JLTYP,FIELD,NFIELD,SNAME,NODE,AREA)
      USE SHARED_VARS
      INCLUDE 'ABA_PARAM.INC'
      DIMENSION H(2),TIME(2),COORDS(3), FIELD(NFIELD)
      CHARACTER*80 SNAME
      REAL*8 x_cur,y_cur,convection,radiation,epsilon,sigma
  
      x_cur = (INT(COORDS(1) * 1.D8 + 0.5D0)) / 1.D8
      y_cur = (INT(COORDS(2) * 1.D8 + 0.5D0)) / 1.D8
      
      sigma   = 5.67D-8
      epsilon = 0.8D0
      
      convection = 10.D0
      radiation  = epsilon*sigma*(TEMP**2.D0+25.D0**2.D0)*(TEMP+25.D0)
      
      H(1) = ZERO
      IF (y_cur.LE.THICKNESS+SMOLL .AND. y_cur.GT.THICKNESS-SMOLL) THEN
        H(1) = convection + radiation
      END IF 
      SINK  = 25.D0
      
      RETURN
      END
      
      
      SUBROUTINE UFIELD(FIELD,KFIELD,NSECPT,KSTEP,KINC,TIME,NODE,COORDS,
     1                  TEMP,DTEMP,NFIELD)
      USE SHARED_VARS
      INCLUDE 'ABA_PARAM.INC'
      DIMENSION FIELD(NSECPT,NFIELD),COORDS(3),TIME(2),TEMP(NSECPT),
     1          DTEMP(NSECPT)

      REAL*8 x_cur,y_cur,k_step,init_fld,layer_number
      LOGICAL heated_state
      
!====== Parameter Initialization ======!
      x_cur = COORDS(1)     ! Current X coordinate
      y_cur = COORDS(2)     ! Current Y coordinate
      k_step = KSTEP        ! Since KTEP itself is not operatble, it is transfered to a REAL*8 variable

      !=== Current Layer Number ===!
      CALL LAYER_NO(TIME(2),ONE,layer_number)
      
!====== FVD Initialization ======!
      ! Global
      IF (STEP.EQ.ZERO) THEN    ! Default value, not chaged by python is 0
        IF (KINC.EQ.ONE .AND. k_step.EQ.ONE) THEN   ! Beginning of the 1st step
            IF (y_cur .LE. THICKNESS*(layer_number-ONE)) THEN
                FIELD(1,1) = ONE    ! Solid
            END IF
            RETURN
        END IF
      ! Local
      ELSE
        IF (KINC.EQ.ONE .AND. k_step.EQ.ONE) THEN   ! Beginning of local 1st step
            init_fld = FIELD(1,1)

            ! Look at temperatures
            IF      (FIELD(1,1).GT.PHASE_T_LQD) THEN
                init_fld = TWO	! Liquid
            ELSE IF (FIELD(1,1).GT.PHASE_T_SLD) THEN
                init_fld = ONE	! Solid
            ELSE
                init_fld = ZERO	! Powder
            END IF
            
            IF (STEP.EQ.ONE .AND. y_cur.LT.ZERO+SMOLL) THEN    ! Below print layers
                init_fld = ONE  ! Solid
            END IF
            
            FIELD(1,1) = init_fld
            RETURN
        END IF
      END IF

!====== Melting ======!
      IF      (TEMP(1).GT.MELT_TEMP) THEN
        FIELD(1,1) = TWO	! Liquid
      ELSE IF (FIELD(1,1).EQ.TWO ) THEN
        FIELD(1,1) = ONE	! Solid
      END IF
      
      RETURN
      END
      
      
	  SUBROUTINE USDFLD(FIELD,STATEV,PNEWDT,DIRECT,T,CELENT,
     1 TIME,DTIME,CMNAME,ORNAME,NFIELD,NSTATV,NOEL,NPT,LAYER,
     2 KSPT,KSTEP,KINC,NDI,NSHR,COORD,JMAC,JMATYP,MATLAYO,LACCFLA)
      USE SHARED_VARS
      INCLUDE 'ABA_PARAM.INC'
      CHARACTER*80 CMNAME,ORNAME
      CHARACTER*3  FLGRAY(15)
      DIMENSION FIELD(NFIELD),STATEV(NSTATV),DIRECT(3,3),
     1 T(3,3),TIME(2)
      DIMENSION ARRAY(15),JARRAY(15),JMAC(*),JMATYP(*),COORD(*)
      REAL*8 y_cur,k_step,layer_number,total_time
      
!====== Parameter Initialization ======!
      x_cur = COORD(1)      ! Current Y coordinate
      y_cur = COORD(2)      ! Current Y coordinate
      k_step = KSTEP        ! Since KTEP itself is not operatble, it is transfered to a REAL*8 variable
      
      !=== Current Layer Number ===!
      CALL LAYER_NO(TIME(2),ZERO,layer_number)
      
      IF (STEP.NE.ZERO .AND. k_step.EQ.TWO) THEN
        RETURN
      END IF
      
      IF (y_cur .GT. THICKNESS*(layer_number) .OR.
     1    x_cur .LT. ZERO - SMOLL .OR.
     2    x_cur .GT. GLOBAL_LENGTH + SMOLL) THEN
        FIELD(2) = ONE     ! Air
	  END IF
      
      RETURN
      END
      
      
      SUBROUTINE LAYER_NO(TIME,DELTA_T,NMBR)
      USE SHARED_VARS
	  INCLUDE 'ABA_PARAM.INC'
      REAL*8,INTENT(IN) :: 
     1          TIME,DELTA_T
      REAL*8,INTENT(OUT):: 
     1          NMBR
      REAL*8    total_time

      IF (DELTA_T.EQ.ONE) THEN
        total_time = TIME + TIME_SHIFT - MIN_INC    ! UFIELD and DFLUX use the time at the end of the increment
                                                    ! This makes sure no numerical error causes issues
      ELSE
        total_time = TIME + TIME_SHIFT + MIN_INC    ! USDFLD uses the time at the beginning of the increment
                                                    ! This makes sure no numerical error causes issues
      END IF
            
      NMBR  = FLOOR(total_time/TTLL_TIME)+ONE
      
      RETURN
      END
      
      
      SUBROUTINE IS_HEATED(X_COORD,Y_COORD,HEAT_STATE)
      USE SHARED_VARS
	  INCLUDE 'ABA_PARAM.INC'
      REAL*8,   INTENT(IN)  :: 
     1          X_COORD,Y_COORD
      LOGICAL,  INTENT(OUT) ::
     1          HEAT_STATE
      
      HEAT_STATE = .TRUE.
      
      IF (Y_COORD.GT.0.18D-3+SMOLL .AND. Y_COORD.LT.1.02D-3-SMOLL) THEN
        IF (X_COORD.GT.0.18D-3+SMOLL .AND. X_COORD.LT.1.01D-3+SMOLL) THEN
            HEAT_STATE = .FALSE.
        END IF
        IF (X_COORD.GT.1.18D-3+SMOLL .AND. X_COORD.LT.2.02D-3+SMOLL) THEN
            HEAT_STATE = .FALSE.
        END IF
      END IF
      
      RETURN
      END